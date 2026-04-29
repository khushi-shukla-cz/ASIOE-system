"""
ASIOE — RAG (Retrieval Augmented Generation) Engine
Attaches real course resources to each learning module.

Pipeline:
1. Build FAISS index from course catalog (Coursera/Kaggle datasets)
2. For each skill in the path, embed the skill description
3. Retrieve top-k matching courses via ANN search
4. Rerank using domain + difficulty alignment
5. Attach best course to each LearningModule
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from core.config import settings
from engines.instrumentation import trace_engine_operation
from schemas.schemas import LearningModule

logger = structlog.get_logger(__name__)

COURSE_CATALOG_PATH = settings.COURSE_CATALOG_PATH
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH


class CourseDocument:
    """Represents a single indexed course."""
    __slots__ = [
        "course_id", "title", "description", "provider",
        "url", "domain", "difficulty_level",
        "estimated_hours", "skills_covered"
    ]

    def __init__(self, data: Dict) -> None:
        self.course_id: str = data["course_id"]
        self.title: str = data["title"]
        self.description: str = data.get("description", "")
        self.provider: str = data.get("provider", "")
        self.url: str = data.get("url", "")
        self.domain: str = data.get("domain", "technical")
        self.difficulty_level: str = data.get("difficulty_level", "intermediate")
        self.estimated_hours: float = float(data.get("estimated_hours", 20.0))
        self.skills_covered: List[str] = data.get("skills_covered", [])


class FAISSCourseIndex:
    """FAISS-backed approximate nearest neighbor search for courses."""

    def __init__(self) -> None:
        self._index: Optional[faiss.IndexFlatIP] = None  # Inner Product = cosine for normalized
        self._documents: List[CourseDocument] = []
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model

    def build_index(self, courses: List[Dict]) -> None:
        """Build FAISS index from course catalog."""
        if not courses:
            logger.warning("rag.index.empty_catalog")
            return

        self._documents = [CourseDocument(c) for c in courses]
        model = self._get_model()

        # Build text representations for embedding
        texts = []
        for course in self._documents:
            text = f"{course.title}. {course.description}. Skills: {', '.join(course.skills_covered[:10])}"
            texts.append(text)

        logger.info("rag.index.building", courses=len(texts))
        embeddings = model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).astype(np.float32)

        # Create FAISS index
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)

        logger.info("rag.index.built", dim=dim, total=len(self._documents))

    def save(self) -> None:
        """Persist index and documents to disk."""
        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(FAISS_INDEX_PATH) + ".bin")
        with open(str(FAISS_INDEX_PATH) + ".pkl", "wb") as f:
            pickle.dump(self._documents, f)
        logger.info("rag.index.saved")

    def load(self) -> bool:
        """Load persisted index from disk."""
        idx_path = str(FAISS_INDEX_PATH) + ".bin"
        doc_path = str(FAISS_INDEX_PATH) + ".pkl"
        if not (Path(idx_path).exists() and Path(doc_path).exists()):
            return False
        self._index = faiss.read_index(idx_path)
        with open(doc_path, "rb") as f:
            self._documents = pickle.load(f)
        logger.info("rag.index.loaded", total=len(self._documents))
        return True

    def search(
        self, query: str, top_k: int = 5
    ) -> List[Tuple[CourseDocument, float]]:
        """Search for courses matching a query string."""
        if self._index is None or not self._documents:
            return []

        model = self._get_model()
        query_emb = model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        ).astype(np.float32)

        k = min(top_k, len(self._documents))
        scores, indices = self._index.search(query_emb, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._documents):
                results.append((self._documents[idx], float(score)))

        return results


class RAGEngine:
    """
    Retrieval-Augmented Course Recommendation Engine.
    Attaches the best matching course to each LearningModule.
    """

    def __init__(self) -> None:
        self._index = FAISSCourseIndex()
        self._initialized = False

    async def initialize(self) -> None:
        """Load or build the FAISS index."""
        if self._initialized:
            return

        # Try loading from cache first
        if self._index.load():
            self._initialized = True
            return

        # Build from course catalog
        if COURSE_CATALOG_PATH.exists():
            with open(COURSE_CATALOG_PATH) as f:
                courses = json.load(f)
            self._index.build_index(courses)
            self._index.save()
        else:
            logger.warning("rag.catalog.missing", path=str(COURSE_CATALOG_PATH))
            self._index.build_index(self._get_fallback_courses())
            self._index.save()

        self._initialized = True

    @trace_engine_operation("rag", "enrich_modules")
    async def enrich_modules(
        self, modules: List[LearningModule]
    ) -> List[LearningModule]:
        """Attach course resources to each module."""
        await self.initialize()

        enriched = []
        for module in modules:
            course = await self._find_best_course(module)
            if course:
                module.course_id = course.course_id
                module.course_title = course.title
                module.course_url = course.url
                module.course_provider = course.provider
                # Optionally update hours from course data
                if course.estimated_hours > 0:
                    module.estimated_hours = course.estimated_hours
            enriched.append(module)

        logger.info("rag.enriched", total=len(enriched))
        return enriched

    async def _find_best_course(
        self, module: LearningModule
    ) -> Optional[CourseDocument]:
        """
        Find the best course for a module using:
        1. Semantic search on skill + domain + difficulty
        2. Rerank by domain and difficulty alignment
        """
        query = (
            f"{module.skill_name} {module.domain} {module.difficulty_level} "
            f"course tutorial learning"
        )

        results = self._index.search(query, top_k=10)
        if not results:
            return None

        # Rerank: boost matches on domain and difficulty
        def rerank_score(doc: CourseDocument, base_score: float) -> float:
            score = base_score
            if doc.domain == module.domain:
                score += 0.15
            if doc.difficulty_level == module.difficulty_level:
                score += 0.10
            # Prefer courses with reasonable duration
            if 5 <= doc.estimated_hours <= 80:
                score += 0.05
            return score

        reranked = sorted(
            results,
            key=lambda x: rerank_score(x[0], x[1]),
            reverse=True,
        )

        return reranked[0][0] if reranked else None

    def _get_fallback_courses(self) -> List[Dict]:
        """Minimal course catalog for cold start."""
        return [
            {
                "course_id": "py_basics", "title": "Python for Everybody",
                "description": "Learn Python programming from scratch",
                "provider": "Coursera", "url": "https://www.coursera.org/specializations/python",
                "domain": "technical", "difficulty_level": "beginner",
                "estimated_hours": 40, "skills_covered": ["Python", "Programming Basics"]
            },
            {
                "course_id": "ml_course", "title": "Machine Learning Specialization",
                "description": "Master machine learning fundamentals with Andrew Ng",
                "provider": "Coursera", "url": "https://www.coursera.org/specializations/machine-learning-introduction",
                "domain": "analytical", "difficulty_level": "intermediate",
                "estimated_hours": 90, "skills_covered": ["Machine Learning", "Python", "Statistics"]
            },
            {
                "course_id": "sql_basics", "title": "SQL for Data Science",
                "description": "SQL fundamentals for data professionals",
                "provider": "Coursera", "url": "https://www.coursera.org/learn/sql-for-data-science",
                "domain": "technical", "difficulty_level": "beginner",
                "estimated_hours": 20, "skills_covered": ["SQL", "Databases", "Data Analysis"]
            },
            {
                "course_id": "dl_course", "title": "Deep Learning Specialization",
                "description": "Build and train deep neural networks",
                "provider": "Coursera", "url": "https://www.coursera.org/specializations/deep-learning",
                "domain": "analytical", "difficulty_level": "advanced",
                "estimated_hours": 120, "skills_covered": ["Deep Learning", "Neural Networks", "TensorFlow"]
            },
            {
                "course_id": "leadership", "title": "Leadership and Management",
                "description": "Develop leadership skills for career advancement",
                "provider": "Coursera", "url": "https://www.coursera.org/specializations/leadership-management-wharton",
                "domain": "leadership", "difficulty_level": "intermediate",
                "estimated_hours": 30, "skills_covered": ["Leadership", "Management", "Communication"]
            },
        ]


_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
