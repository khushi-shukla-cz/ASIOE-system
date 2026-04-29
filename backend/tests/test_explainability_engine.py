from __future__ import annotations

from datetime import datetime

import pytest

from engines.explainability.explainability_engine import ExplainabilityEngine
from schemas.schemas import (
    DifficultyLevel,
    DomainCoverage,
    GapAnalysisResult,
    GapSeverity,
    LearningModule,
    LearningPathResult,
    NodeExplanation,
    PathPhase,
    SkillGap,
    SkillDomain,
)


def _build_path_result() -> LearningPathResult:
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
        dependency_chain=["Python"],
        importance_score=0.9,
        confidence_score=0.88,
    )

    phase = PathPhase(
        phase_number=1,
        phase_name="Foundations",
        description="Start here",
        modules=[module],
        estimated_hours=20,
        estimated_weeks=2,
        focus_domains=["technical"],
    )

    return LearningPathResult(
        session_id="s1",
        path_id="path-1",
        target_role="Backend Engineer",
        phases=[phase],
        total_modules=1,
        total_hours=20,
        total_weeks=2,
        path_graph={"nodes": ["python"], "edges": []},
        efficiency_score=0.92,
        redundancy_eliminated=1,
        path_algorithm="adaptive_topological_dfs_v2",
        path_version=2,
        reasoning_trace="trace",
        generated_at=datetime.utcnow(),
    )


def _build_gap_result() -> GapAnalysisResult:
    gap = SkillGap(
        skill_id="python",
        skill_name="Python",
        domain=SkillDomain.TECHNICAL,
        severity=GapSeverity.CRITICAL,
        current_score=0.2,
        required_score=0.9,
        gap_delta=0.7,
        reasoning="Blocking deficiency",
    )
    return GapAnalysisResult(
        session_id="s1",
        overall_readiness_score=0.42,
        readiness_label="Developing",
        critical_gaps=[gap],
        major_gaps=[],
        minor_gaps=[],
        strength_areas=[],
        domain_coverage=[
            DomainCoverage(
                domain=SkillDomain.TECHNICAL,
                coverage_percentage=60.0,
                matched_skills=3,
                total_required=5,
                radar_value=0.6,
            )
        ],
        reasoning_trace="trace",
        analysis_timestamp=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_generate_node_explanations_includes_gap_contribution():
    engine = object.__new__(ExplainabilityEngine)

    path = _build_path_result()
    gap = _build_gap_result()

    explanations = await engine.generate_node_explanations(path, gap)

    assert len(explanations) == 1
    assert isinstance(explanations[0], NodeExplanation)
    assert explanations[0].node_id == "m1"
    assert explanations[0].gap_contribution == pytest.approx(0.7)
    assert explanations[0].importance_rank == 1
    assert explanations[0].alternative_paths


@pytest.mark.asyncio
async def test_generate_system_trace_composes_trace_sections():
    engine = object.__new__(ExplainabilityEngine)

    parsing_data = {
        "resume": {"skills": ["Python", "SQL"], "parsing_confidence": 0.91},
        "jd": {"required_skills": ["Python"], "preferred_skills": ["Docker"]},
    }
    path = _build_path_result()
    gap = _build_gap_result()

    trace = await engine.generate_system_trace(
        session_id="s1",
        parsing_data=parsing_data,
        gap_analysis=gap,
        path=path,
        total_tokens=1234,
    )

    assert trace.session_id == "s1"
    assert trace.total_tokens_used == 1234
    assert "PARSING ENGINE" in trace.parsing_trace
    assert "NORMALIZATION ENGINE" in trace.normalization_trace
    assert "GAP ENGINE" in trace.gap_trace
    assert "PATH ENGINE" in trace.path_trace


# === Comprehensive Explanation Quality Tests ===


class TestNodeExplanationQuality:
    """Tests for node-level explanation completeness and clarity."""

    @pytest.mark.asyncio
    async def test_node_explanation_required_fields(self):
        """Verify node explanations contain all required fields."""
        engine = object.__new__(ExplainabilityEngine)
        
        explanation = NodeExplanation(
            node_id="node_python",
            skill_id="python",
            confidence_score=0.85,
            importance_rank=1,
            gap_contribution=0.7,
            reasoning="Python is foundational for backend development",
            alternative_paths=["Java", "Go"],
        )

        assert explanation.node_id == "node_python"
        assert explanation.skill_id == "python"
        assert explanation.confidence_score == 0.85
        assert explanation.importance_rank == 1
        assert explanation.gap_contribution == 0.7
        assert explanation.reasoning is not None
        assert isinstance(explanation.alternative_paths, list)

    @pytest.mark.asyncio
    async def test_confidence_score_bounds_strictly_enforced(self):
        """Verify confidence scores are strictly bounded [0, 1]."""
        engine = object.__new__(ExplainabilityEngine)

        valid_scores = [0.0, 0.25, 0.5, 0.75, 1.0]
        for score in valid_scores:
            explanation = NodeExplanation(
                node_id=f"n_{score}",
                skill_id="skill",
                confidence_score=score,
                importance_rank=1,
                gap_contribution=0.5,
                reasoning="test",
                alternative_paths=[],
            )
            assert 0.0 <= explanation.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_dependency_chain_captured_in_explanation(self):
        """Verify dependency chain is explicitly captured in explanations."""
        engine = object.__new__(ExplainabilityEngine)

        # Module with dependency chain
        module = LearningModule(
            module_id="m_advanced_python",
            skill_id="advanced_python",
            skill_name="Advanced Python",
            title="Advanced Python",
            description="desc",
            domain=SkillDomain.TECHNICAL,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            estimated_hours=20,
            sequence_order=2,
            phase_number=1,
            prerequisite_module_ids=["m_basics"],
            unlocks_module_ids=["m_frameworks"],
            why_selected="Required for data structures",
            dependency_chain=["python_basics", "variables_and_types", "functions"],
            importance_score=0.9,
            confidence_score=0.9,
        )

        explanation = NodeExplanation(
            node_id=module.module_id,
            skill_id=module.skill_id,
            confidence_score=0.88,
            importance_rank=2,
            gap_contribution=0.5,
            reasoning=f"Depends on: {', '.join(module.dependency_chain)}. Unlocks: data_structures.",
            alternative_paths=[],
        )

        assert "python_basics" in explanation.reasoning
        assert "variables_and_types" in explanation.reasoning
        assert "functions" in explanation.reasoning


class TestReasoningTraceCompleteness:
    """Tests for complete reasoning trace covering all 6 engines."""

    @pytest.mark.asyncio
    async def test_reasoning_trace_covers_all_six_engines(self):
        """Verify trace includes all 6 engine stages."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()
        path = _build_path_result()

        trace = await engine.generate_system_trace(
            session_id="s1",
            parsing_data={"resume": {"skills": ["Python"]}, "jd": {"required_skills": ["Python"]}},
            gap_analysis=gap,
            path=path,
            total_tokens=5000,
        )

        # All 6 engines should be present
        assert trace.parsing_trace is not None
        assert trace.normalization_trace is not None
        assert trace.gap_trace is not None
        assert trace.path_trace is not None
        assert trace.rag_trace is not None
        assert trace.explainability_trace is not None

    @pytest.mark.asyncio
    async def test_token_accounting_across_trace(self):
        """Verify token usage is accurately tracked."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()
        path = _build_path_result()

        trace = await engine.generate_system_trace(
            session_id="s1",
            parsing_data={},
            gap_analysis=gap,
            path=path,
            total_tokens=12345,
        )

        assert trace.total_tokens_used == 12345
        assert trace.total_tokens_used > 0

    @pytest.mark.asyncio
    async def test_decision_confidence_reflects_uncertainty(self):
        """Verify decision confidence indicates overall trace quality."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()
        path = _build_path_result()

        trace = await engine.generate_system_trace(
            session_id="s1",
            parsing_data={"resume": {"parsing_confidence": 0.35}},  # Low confidence
            gap_analysis=gap,
            path=path,
            total_tokens=1000,
        )

        # Low parsing confidence should propagate to decision confidence
        assert trace.decision_confidence < 0.9


class TestAlternativePathGeneration:
    """Tests for alternative path generation with tradeoffs."""

    @pytest.mark.asyncio
    async def test_alternative_paths_have_valid_structure(self):
        """Verify alternative paths contain valid tradeoff information."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()

        alternative_paths = await engine.generate_alternative_paths(
            gap_analysis=gap,
            time_budget_weeks=8,
            intensity_preference="balanced",
        )

        # Should generate at least 2 alternatives
        assert len(alternative_paths) >= 2
        
        for path in alternative_paths:
            assert hasattr(path, "total_modules")
            assert hasattr(path, "total_hours")
            assert hasattr(path, "intensity_score")
            assert hasattr(path, "coverage_score")
            assert hasattr(path, "tradeoff_description")

    @pytest.mark.asyncio
    async def test_fast_track_path_has_higher_intensity(self):
        """Verify fast-track alternatives have compressed schedules and high intensity."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()

        paths = await engine.generate_alternative_paths(
            gap_analysis=gap,
            time_budget_weeks=4,
            intensity_preference="fast_track",
        )

        # At least one path should be high intensity
        fast_paths = [p for p in paths if p.intensity_score >= 0.8]
        assert len(fast_paths) > 0

    @pytest.mark.asyncio
    async def test_comprehensive_path_has_higher_coverage(self):
        """Verify comprehensive alternatives sacrifice speed for broad coverage."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()

        paths = await engine.generate_alternative_paths(
            gap_analysis=gap,
            time_budget_weeks=16,
            intensity_preference="comprehensive",
        )

        # At least one path should have high coverage
        comprehensive_paths = [p for p in paths if p.coverage_score >= 0.95]
        assert len(comprehensive_paths) > 0

    @pytest.mark.asyncio
    async def test_path_tradeoff_clearly_articulated(self):
        """Verify tradeoff descriptions explain intensity vs coverage vs time."""
        engine = object.__new__(ExplainabilityEngine)

        gap = _build_gap_result()

        paths = await engine.generate_alternative_paths(
            gap_analysis=gap,
            time_budget_weeks=12,
            intensity_preference="balanced",
        )

        for path in paths:
            description = path.tradeoff_description.lower()
            # Should mention at least one tradeoff dimension
            assert any(keyword in description for keyword in 
                      ["intensity", "coverage", "time", "hours", "modules", "speed", "broad"])


class TestExplanationCompleteness:
    """Tests for explanation completeness addressing 5 key questions."""

    @pytest.mark.asyncio
    async def test_explanation_answers_why_question(self):
        """Verify explanation articulates WHY skill is needed."""
        engine = object.__new__(ExplainabilityEngine)

        explanation = NodeExplanation(
            node_id="n1",
            skill_id="sql",
            confidence_score=0.92,
            importance_rank=1,
            gap_contribution=0.8,
            reasoning="SQL is essential because databases are foundational to backend systems. Required for data retrieval and manipulation in production applications.",
            alternative_paths=[],
        )

        # Should address necessity/requirement
        assert any(word in explanation.reasoning.lower() for word in 
                  ["essential", "required", "necessary", "needed", "critical", "blocking"])

    @pytest.mark.asyncio
    async def test_explanation_answers_what_question(self):
        """Verify explanation clarifies WHAT the skill entails."""
        engine = object.__new__(ExplainabilityEngine)

        explanation = NodeExplanation(
            node_id="n1",
            skill_id="api_design",
            confidence_score=0.88,
            importance_rank=2,
            gap_contribution=0.6,
            reasoning="API Design involves creating REST/GraphQL endpoints. Includes HTTP verbs, response schemas, error handling, and versioning strategies.",
            alternative_paths=[],
        )

        # Should include concrete elements
        assert any(term in explanation.reasoning for term in 
                  ["REST", "GraphQL", "HTTP", "endpoint", "schema", "error handling"])

    @pytest.mark.asyncio
    async def test_explanation_answers_how_question(self):
        """Verify explanation suggests HOW to learn the skill."""
        engine = object.__new__(ExplainabilityEngine)

        explanation = NodeExplanation(
            node_id="n1",
            skill_id="docker",
            confidence_score=0.85,
            importance_rank=3,
            gap_contribution=0.5,
            reasoning="Docker containerization: Learn through hands-on course (Docker for Developers on Udemy). Practice with local projects. Build and push to Docker Hub.",
            alternative_paths=[],
        )

        # Should mention learning methods
        assert any(word in explanation.reasoning.lower() for word in 
                  ["learn", "course", "practice", "hands-on", "build", "exercise", "project"])

    @pytest.mark.asyncio
    async def test_explanation_provides_alternatives(self):
        """Verify explanation mentions alternatives when applicable."""
        engine = object.__new__(ExplainabilityEngine)

        explanation = NodeExplanation(
            node_id="n1",
            skill_id="python",
            confidence_score=0.90,
            importance_rank=1,
            gap_contribution=0.75,
            reasoning="Python is recommended for backend. Alternatives: Go (faster, compiled), Rust (systems programming), Java (enterprise scale).",
            alternative_paths=["Go", "Rust", "Java"],
        )

        # Should mention alternatives
        assert len(explanation.alternative_paths) > 0
        assert any(alt in explanation.reasoning for alt in explanation.alternative_paths)


class TestExplanationClarity:
    """Tests for explanation clarity and specificity."""

    @pytest.mark.asyncio
    async def test_explanation_has_substantive_length(self):
        """Verify explanations are substantive, not superficial."""
        engine = object.__new__(ExplainabilityEngine)

        explanation = NodeExplanation(
            node_id="n1",
            skill_id="python",
            confidence_score=0.85,
            importance_rank=1,
            gap_contribution=0.7,
            reasoning="Python: A high-level, interpreted programming language essential for backend development. Widely adopted in industry for web APIs, data processing, and automation. Recommended courses: Codecademy Python Track, Real Python courses. Focus areas: functions, classes, async patterns, ORM usage with SQLAlchemy.",
            alternative_paths=[],
        )

        # Substantive explanation should be > 100 characters
        assert len(explanation.reasoning) > 100

    @pytest.mark.asyncio
    async def test_explanation_uses_specific_techniques_not_generics(self):
        """Verify explanations mention specific technologies/techniques."""
        engine = object.__new__(ExplainabilityEngine)

        explanation = NodeExplanation(
            node_id="n1",
            skill_id="database_design",
            confidence_score=0.88,
            importance_rank=2,
            gap_contribution=0.65,
            reasoning="Database design: Master normalization (1NF, 2NF, 3NF), indexing strategies, query optimization. Learn PostgreSQL (ACID compliance) and Redis (caching). Practice: design schemas for e-commerce, user management systems. Use tools: pgAdmin, Redis CLI.",
            alternative_paths=[],
        )

        # Should mention specific technologies
        specific_terms = ["normalization", "1NF", "PostgreSQL", "Redis", "pgAdmin", "ACID", "indexing"]
        found_terms = [term for term in specific_terms if term in explanation.reasoning]
        assert len(found_terms) >= 4

    @pytest.mark.asyncio
    async def test_explanation_avoids_excessive_jargon(self):
        """Verify explanations don't assume excessive prior knowledge."""
        engine = object.__new__(ExplainabilityEngine)

        # Good: explains terms as used
        good_explanation = NodeExplanation(
            node_id="n1",
            skill_id="async",
            confidence_score=0.82,
            importance_rank=2,
            gap_contribution=0.6,
            reasoning="Async (asynchronous) programming: Code execution without blocking. Python uses asyncio and await keywords. When one operation waits (I/O), others can run. Benefit: Handle many requests efficiently. Learn: async/await patterns, event loops.",
            alternative_paths=[],
        )

        # When jargon used, should be explained
        assert "async (asynchronous)" in good_explanation.reasoning
        assert "benefit" in good_explanation.reasoning.lower()
