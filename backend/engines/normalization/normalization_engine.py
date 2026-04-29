"""
ASIOE — Skill Normalization Engine
Maps free-text extracted skills to canonical skill IDs using:
1. Exact match against skill ontology
2. Semantic similarity via sentence-transformers
3. Fuzzy cluster-based matching

This eliminates duplicates and synonyms (e.g., "JS" → "JavaScript",
"ML" → "Machine Learning") before the graph is built.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from core.config import settings
from engines.instrumentation import trace_engine_operation

logger = structlog.get_logger(__name__)

# Path to the canonical skill ontology (seeded from O*NET + manual curation)
ONTOLOGY_PATH = settings.SKILL_ONTOLOGY_PATH
EMBEDDINGS_CACHE_PATH = settings.ONTOLOGY_EMBEDDINGS_CACHE_PATH


class SkillOntology:
    """
    In-memory canonical skill registry.
    Each entry: {skill_id, canonical_name, aliases, domain, difficulty, onet_code, ...}
    """

    def __init__(self, skills: List[Dict]) -> None:
        self.skills = skills
        # Build lookup indexes
        self._by_id: Dict[str, Dict] = {s["skill_id"]: s for s in skills}
        self._by_canonical: Dict[str, str] = {
            s["canonical_name"].lower(): s["skill_id"] for s in skills
        }
        self._alias_map: Dict[str, str] = {}
        for skill in skills:
            for alias in skill.get("aliases", []):
                self._alias_map[alias.lower()] = skill["skill_id"]

    def lookup_exact(self, name: str) -> Optional[str]:
        """Return skill_id for exact name match (canonical or alias)."""
        key = name.lower().strip()
        return self._by_canonical.get(key) or self._alias_map.get(key)

    def get_skill(self, skill_id: str) -> Optional[Dict]:
        return self._by_id.get(skill_id)

    def all_canonical_names(self) -> List[str]:
        return [s["canonical_name"] for s in self.skills]

    def all_skill_ids(self) -> List[str]:
        return list(self._by_id.keys())

    def __len__(self) -> int:
        return len(self.skills)


class SkillNormalizationEngine:
    """
    Normalizes extracted skill names to canonical ontology entries.
    Uses a three-pass strategy for maximum accuracy.
    """

    def __init__(self) -> None:
        self._model: Optional[SentenceTransformer] = None
        self._ontology: Optional[SkillOntology] = None
        self._ontology_embeddings: Optional[np.ndarray] = None
        self._threshold = settings.SKILL_SIMILARITY_THRESHOLD

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("normalization.model.loading", model=settings.EMBEDDING_MODEL)
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("normalization.model.loaded")
        return self._model

    def _load_ontology(self) -> SkillOntology:
        if self._ontology is None:
            if not ONTOLOGY_PATH.exists():
                logger.warning("normalization.ontology.missing", path=str(ONTOLOGY_PATH))
                self._ontology = SkillOntology(self._build_fallback_ontology())
            else:
                with open(ONTOLOGY_PATH) as f:
                    skills = json.load(f)
                self._ontology = SkillOntology(skills)
            logger.info("normalization.ontology.loaded", count=len(self._ontology))
        return self._ontology

    def _load_ontology_embeddings(self) -> np.ndarray:
        if self._ontology_embeddings is None:
            ontology = self._load_ontology()
            if EMBEDDINGS_CACHE_PATH.exists():
                with open(EMBEDDINGS_CACHE_PATH, "rb") as f:
                    cached = pickle.load(f)
                if cached.get("count") == len(ontology):
                    self._ontology_embeddings = cached["embeddings"]
                    logger.info("normalization.embeddings.cache_hit")
                    return self._ontology_embeddings

            logger.info("normalization.embeddings.computing")
            model = self._load_model()
            names = ontology.all_canonical_names()
            embeddings = model.encode(
                names,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            self._ontology_embeddings = embeddings
            # Cache to disk
            EMBEDDINGS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(EMBEDDINGS_CACHE_PATH, "wb") as f:
                pickle.dump({"count": len(ontology), "embeddings": embeddings}, f)
            logger.info("normalization.embeddings.cached", count=len(names))
        return self._ontology_embeddings

    def normalize_skill(
        self, skill_name: str, domain_hint: Optional[str] = None
    ) -> Tuple[Optional[str], float]:
        """
        Normalize a single skill name to canonical skill_id.
        Returns (skill_id | None, confidence_score).
        """
        ontology = self._load_ontology()

        # Pass 1: Exact match (fastest, highest confidence)
        exact_id = ontology.lookup_exact(skill_name)
        if exact_id:
            return exact_id, 1.0

        # Pass 2: Semantic similarity
        model = self._load_model()
        query_emb = model.encode(
            [skill_name], normalize_embeddings=True, show_progress_bar=False
        )
        onto_embs = self._load_ontology_embeddings()

        similarities = cosine_similarity(query_emb, onto_embs)[0]
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        if best_score >= self._threshold:
            canonical_names = ontology.all_canonical_names()
            matched_name = canonical_names[best_idx]
            skill_id = ontology.lookup_exact(matched_name)
            logger.debug(
                "normalization.semantic_match",
                input=skill_name,
                matched=matched_name,
                score=round(best_score, 3),
            )
            return skill_id, best_score

        # Pass 3: No match — generate a synthetic skill_id
        synthetic_id = f"custom_{skill_name.lower().replace(' ', '_')}"
        logger.debug("normalization.no_match", skill=skill_name, best_score=best_score)
        return synthetic_id, best_score

    @trace_engine_operation("normalization", "normalize_skill_list")
    def normalize_skill_list(
        self, skills: List[Dict]
    ) -> List[Dict]:
        """
        Normalize a list of extracted skills.
        Adds canonical_skill_id and normalization_confidence to each.
        Deduplicates by canonical_id, keeping highest confidence.
        """
        seen: Dict[str, Dict] = {}

        for skill in skills:
            name = skill.get("name", "")
            if not name:
                continue

            skill_id, conf = self.normalize_skill(name, skill.get("domain"))

            normalized = {
                **skill,
                "canonical_skill_id": skill_id,
                "normalization_confidence": round(conf, 4),
            }

            # Deduplicate — keep higher-confidence entry
            existing = seen.get(skill_id)
            if existing is None:
                seen[skill_id] = normalized
            elif conf > existing.get("normalization_confidence", 0):
                seen[skill_id] = normalized

        result = list(seen.values())
        logger.info(
            "normalization.complete",
            input_count=len(skills),
            output_count=len(result),
            dedup_removed=len(skills) - len(result),
        )
        return result

    def embed_skills_for_rag(self, skill_names: List[str]) -> np.ndarray:
        """Produce embeddings for a list of skill names (used by RAG engine)."""
        model = self._load_model()
        return model.encode(
            skill_names,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def _build_fallback_ontology(self) -> List[Dict]:
        """Minimal ontology for when seed data is unavailable."""
        return [
            {
                "skill_id": "python", "canonical_name": "Python",
                "aliases": ["python3", "python 3", "py"],
                "domain": "technical", "difficulty_level": "intermediate",
                "avg_time_to_learn_hours": 80, "importance_score": 0.95,
                "prerequisites": [], "onet_code": "2.C.7.e"
            },
            {
                "skill_id": "machine_learning", "canonical_name": "Machine Learning",
                "aliases": ["ml", "statistical learning"],
                "domain": "analytical", "difficulty_level": "advanced",
                "avg_time_to_learn_hours": 160, "importance_score": 0.9,
                "prerequisites": ["python", "statistics", "linear_algebra"],
                "onet_code": "2.C.7.f"
            },
            {
                "skill_id": "sql", "canonical_name": "SQL",
                "aliases": ["structured query language", "mysql", "postgresql", "postgres"],
                "domain": "technical", "difficulty_level": "intermediate",
                "avg_time_to_learn_hours": 40, "importance_score": 0.88,
                "prerequisites": [], "onet_code": "2.C.7.b"
            },
        ]


_normalization_engine: Optional[SkillNormalizationEngine] = None


def get_normalization_engine() -> SkillNormalizationEngine:
    global _normalization_engine
    if _normalization_engine is None:
        _normalization_engine = SkillNormalizationEngine()
    return _normalization_engine
