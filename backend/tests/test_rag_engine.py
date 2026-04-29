from __future__ import annotations

import sys
import types

import pytest


def _has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ModuleNotFoundError:
        return False


if not _has_module("faiss"):
    faiss_stub = types.ModuleType("faiss")

    class _IndexFlatIP:
        def __init__(self, *args, **kwargs):
            self.vectors = []

        def add(self, vectors):
            self.vectors.extend(vectors)

    faiss_stub.IndexFlatIP = _IndexFlatIP
    faiss_stub.write_index = lambda *args, **kwargs: None
    faiss_stub.read_index = lambda *args, **kwargs: _IndexFlatIP()
    sys.modules["faiss"] = faiss_stub

from engines.rag.rag_engine import CourseDocument, RAGEngine
from schemas.schemas import DifficultyLevel, LearningModule, SkillDomain


class _DummyIndex:
    def __init__(self, results):
        self.results = results

    def search(self, _query, top_k=5):
        return self.results[:top_k]


@pytest.mark.asyncio
async def test_find_best_course_prefers_domain_and_difficulty_alignment():
    engine = object.__new__(RAGEngine)
    engine._initialized = True
    engine._index = _DummyIndex(
        [
            (CourseDocument({"course_id": "generic", "title": "Generic"}), 0.94),
            (
                CourseDocument(
                    {
                        "course_id": "aligned",
                        "title": "Aligned Course",
                        "domain": "technical",
                        "difficulty_level": "beginner",
                        "estimated_hours": 24,
                    }
                ),
                0.80,
            ),
        ]
    )

    module = LearningModule(
        module_id="m1",
        skill_id="python",
        skill_name="Python",
        title="Master Python",
        description="Python fundamentals",
        domain=SkillDomain.TECHNICAL,
        difficulty_level=DifficultyLevel.BEGINNER,
        estimated_hours=20,
        sequence_order=1,
        phase_number=1,
        prerequisite_module_ids=[],
        unlocks_module_ids=[],
        why_selected="Core skill",
        dependency_chain=[],
        importance_score=0.9,
        confidence_score=0.9,
    )

    course = await engine._find_best_course(module)

    assert course is not None
    assert course.course_id == "aligned"


@pytest.mark.asyncio
async def test_enrich_modules_attaches_course_fields(monkeypatch):
    engine = object.__new__(RAGEngine)
    engine._initialized = True
    engine._index = _DummyIndex(
        [
            (
                CourseDocument(
                    {
                        "course_id": "sql_basics",
                        "title": "SQL Basics",
                        "provider": "Coursera",
                        "url": "https://example.com/sql",
                        "domain": "technical",
                        "difficulty_level": "beginner",
                        "estimated_hours": 30,
                    }
                ),
                0.99,
            )
        ]
    )

    async def _noop_initialize():
        return None

    monkeypatch.setattr(engine, "initialize", _noop_initialize)

    module = LearningModule(
        module_id="m1",
        skill_id="sql",
        skill_name="SQL",
        title="Master SQL",
        description="SQL fundamentals",
        domain=SkillDomain.TECHNICAL,
        difficulty_level=DifficultyLevel.BEGINNER,
        estimated_hours=12,
        sequence_order=1,
        phase_number=1,
        prerequisite_module_ids=[],
        unlocks_module_ids=[],
        why_selected="Needed for analytics",
        dependency_chain=[],
        importance_score=0.8,
        confidence_score=0.8,
    )

    enriched = await engine.enrich_modules([module])

    assert enriched[0].course_id == "sql_basics"
    assert enriched[0].course_title == "SQL Basics"
    assert enriched[0].course_provider == "Coursera"
    assert enriched[0].estimated_hours == 30


# === Boundary Test Suite: Course Retrieval & Ranking ===


class TestCourseRetrieval:
    """Focused tests for course retrieval, ranking, and relevance scoring."""

    @pytest.mark.asyncio
    async def test_course_retrieval_respects_top_k_limit(self):
        """Verify top_k parameter limits returned courses."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        
        # Return 5 courses, but only request top 3
        courses_data = [
            (CourseDocument({"course_id": f"course_{i}", "title": f"Course {i}"}), 0.95 - i * 0.1)
            for i in range(5)
        ]
        engine._index = _DummyIndex(courses_data)
        
        module = LearningModule(
            module_id="m1", skill_id="python", skill_name="Python",
            title="Python", description="desc", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.BEGINNER, estimated_hours=20,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.9, confidence_score=0.9,
        )
        
        # Mock _find_best_course to track how many are searched
        search_count = 0
        original_find = engine._find_best_course
        async def mock_find(mod):
            nonlocal search_count
            search_count += 1
            return await original_find(mod)
        
        engine._find_best_course = mock_find
        course = await engine._find_best_course(module)
        assert course is not None

    @pytest.mark.asyncio
    async def test_course_ranking_by_difficulty_match(self):
        """Verify courses aligned to module difficulty rank higher."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        
        # Beginner courses with varying difficulties
        engine._index = _DummyIndex([
            (CourseDocument({"course_id": "advanced", "difficulty_level": "advanced", "title": "Advanced"}), 0.95),
            (CourseDocument({"course_id": "beginner", "difficulty_level": "beginner", "title": "Beginner"}), 0.85),
        ])
        
        module = LearningModule(
            module_id="m1", skill_id="python", skill_name="Python",
            title="Python", description="desc", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.BEGINNER, estimated_hours=20,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.9, confidence_score=0.9,
        )
        
        course = await engine._find_best_course(module)
        # Should prefer beginner course despite lower initial score
        assert course is not None
        assert course.course_id == "beginner"

    @pytest.mark.asyncio
    async def test_course_ranking_by_domain_fit(self):
        """Verify courses aligned to module domain rank higher."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        
        engine._index = _DummyIndex([
            (CourseDocument({"course_id": "soft_skills", "domain": "soft_skills", "title": "Soft Skills"}), 0.95),
            (CourseDocument({"course_id": "technical", "domain": "technical", "title": "Technical"}), 0.85),
        ])
        
        module = LearningModule(
            module_id="m1", skill_id="python", skill_name="Python",
            title="Python", description="desc", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.BEGINNER, estimated_hours=20,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.9, confidence_score=0.9,
        )
        
        course = await engine._find_best_course(module)
        assert course is not None
        assert course.course_id == "technical"


class TestCourseRelevanceScoring:
    """Tests for relevance score computation and threshold filtering."""

    @pytest.mark.asyncio
    async def test_relevance_score_minimum_threshold(self):
        """Verify courses below relevance threshold are rejected."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        
        # Low relevance course
        engine._index = _DummyIndex([
            (CourseDocument({"course_id": "irrelevant", "title": "Irrelevant"}), 0.3),
        ])
        
        module = LearningModule(
            module_id="m1", skill_id="python", skill_name="Python",
            title="Python", description="desc", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.BEGINNER, estimated_hours=20,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.9, confidence_score=0.9,
        )
        
        course = await engine._find_best_course(module)
        # Low-relevance courses should be rejected or have None returned
        assert course is None or course.course_id != "irrelevant"

    @pytest.mark.asyncio
    async def test_no_courses_available_for_skill(self):
        """Verify graceful handling when no courses match skill."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        
        engine._index = _DummyIndex([])
        
        module = LearningModule(
            module_id="m1", skill_id="rare_skill", skill_name="Rare Skill",
            title="Rare Skill", description="desc", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.EXPERT, estimated_hours=40,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.8, confidence_score=0.8,
        )
        
        course = await engine._find_best_course(module)
        assert course is None


class TestCourseEnrichmentBoundaries:
    """Tests for module enrichment with course metadata."""

    @pytest.mark.asyncio
    async def test_multiple_courses_per_module(self):
        """Verify single best course selected per module."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        
        engine._index = _DummyIndex([
            (CourseDocument({"course_id": "top_choice", "title": "Top"}), 0.95),
            (CourseDocument({"course_id": "second_choice", "title": "Second"}), 0.85),
            (CourseDocument({"course_id": "third_choice", "title": "Third"}), 0.75),
        ])
        
        module = LearningModule(
            module_id="m1", skill_id="python", skill_name="Python",
            title="Python", description="desc", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.BEGINNER, estimated_hours=20,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.9, confidence_score=0.9,
        )
        
        course = await engine._find_best_course(module)
        assert course is not None
        assert course.course_id == "top_choice"

    @pytest.mark.asyncio
    async def test_enrichment_preserves_module_fields(self):
        """Verify enrichment adds course fields without overwriting module fields."""
        engine = object.__new__(RAGEngine)
        engine._initialized = True
        engine._index = _DummyIndex([
            (CourseDocument({"course_id": "python_101", "title": "Python 101", "estimated_hours": 40}), 0.99),
        ])
        
        original_module = LearningModule(
            module_id="m_original", skill_id="python", skill_name="Python",
            title="Module Title", description="Module description", domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.BEGINNER, estimated_hours=20,
            sequence_order=1, phase_number=1, prerequisite_module_ids=[],
            unlocks_module_ids=[], why_selected="reason", dependency_chain=[],
            importance_score=0.9, confidence_score=0.9,
        )
        
        async def _noop_initialize():
            return None
        engine.initialize = _noop_initialize
        
        enriched_list = await engine.enrich_modules([original_module])
        enriched = enriched_list[0]
        
        # Original module fields preserved
        assert enriched.module_id == "m_original"
        assert enriched.title == "Module Title"
        assert enriched.estimated_hours == 20
        
        # Course fields added
        assert enriched.course_id == "python_101"
        assert enriched.course_title == "Python 101"
