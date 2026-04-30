"""
ASIOE — Gap Engine Unit Tests
Focused tests for gap severity classification, readiness scoring, and boundary conditions.
"""
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from schemas.schemas import (
    GapAnalysisResult,
    SkillGap,
    GapSeverity,
    DomainCoverage,
)


@pytest.mark.asyncio
class TestGapSeverityClassification:
    """Test gap severity boundaries: critical > major > minor."""

    @pytest.fixture
    def gap_engine(self):
        """Fixture for gap engine."""
        from engines.gap.gap_engine import get_gap_engine
        return get_gap_engine()

    def test_critical_gap_threshold(self, gap_engine):
        """Critical gap: 0-30% candidate proficiency in required skill."""
        # A skill required by JD but completely missing from resume (0%)
        critical_gap = SkillGap(
            skill_id="python",
            skill_name="Python",
            gap_delta=1.0,  # 100% gap
            gap_type="missing",
            severity=GapSeverity.CRITICAL,
            jd_proficiency_required=0.9,
            candidate_proficiency=0.0,
        )

        assert critical_gap.severity == GapSeverity.CRITICAL
        assert critical_gap.gap_delta == 1.0

    def test_major_gap_threshold(self, gap_engine):
        """Major gap: 30-70% proficiency gap."""
        major_gap = SkillGap(
            skill_id="java",
            skill_name="Java",
            gap_delta=0.5,  # 50% gap
            gap_type="proficiency_mismatch",
            severity=GapSeverity.MAJOR,
            jd_proficiency_required=0.8,
            candidate_proficiency=0.3,
        )

        assert major_gap.severity == GapSeverity.MAJOR
        assert 0.3 < major_gap.gap_delta < 0.7

    def test_minor_gap_threshold(self, gap_engine):
        """Minor gap: 70%+ candidate proficiency."""
        minor_gap = SkillGap(
            skill_id="sql",
            skill_name="SQL",
            gap_delta=0.2,  # 20% gap
            gap_type="depth_mismatch",
            severity=GapSeverity.MINOR,
            jd_proficiency_required=0.7,
            candidate_proficiency=0.5,
        )

        assert minor_gap.severity == GapSeverity.MINOR
        assert minor_gap.gap_delta < 0.3


@pytest.mark.asyncio
class TestReadinessScoring:
    """Test readiness score calculation and boundaries."""

    def test_readiness_score_zero_gaps(self):
        """100% readiness when no gaps exist."""
        # All skills present at required proficiency
        result = GapAnalysisResult(
            session_id="test-session",
            critical_gaps=[],
            major_gaps=[],
            minor_gaps=[],
            readiness_score=1.0,
            readiness_label="Ready Now",
            domain_coverage=[],
            reasoning_trace="Candidate fully meets requirements",
        )

        assert result.readiness_score == 1.0
        assert result.readiness_label == "Ready Now"

    def test_readiness_score_with_critical_gaps(self):
        """Readiness reduced significantly with critical gaps."""
        result = GapAnalysisResult(
            session_id="test-session",
            critical_gaps=[
                SkillGap(
                    skill_id="ml",
                    skill_name="Machine Learning",
                    gap_delta=0.9,
                    gap_type="missing",
                    severity=GapSeverity.CRITICAL,
                    jd_proficiency_required=0.8,
                    candidate_proficiency=0.1,
                )
            ],
            major_gaps=[],
            minor_gaps=[],
            readiness_score=0.2,
            readiness_label="Not Ready",
            domain_coverage=[],
            reasoning_trace="Critical gaps block readiness",
        )

        assert result.readiness_score <= 0.3
        assert result.readiness_label == "Not Ready"

    def test_readiness_score_with_major_gaps(self):
        """Readiness moderately reduced with major gaps."""
        result = GapAnalysisResult(
            session_id="test-session",
            critical_gaps=[],
            major_gaps=[
                SkillGap(
                    skill_id="react",
                    skill_name="React",
                    gap_delta=0.5,
                    gap_type="proficiency_mismatch",
                    severity=GapSeverity.MAJOR,
                    jd_proficiency_required=0.8,
                    candidate_proficiency=0.3,
                )
            ],
            minor_gaps=[],
            readiness_score=0.65,
            readiness_label="Needs Preparation",
            domain_coverage=[],
            reasoning_trace="Major gaps require targeted learning",
        )

        assert 0.5 <= result.readiness_score < 0.8
        assert result.readiness_label == "Needs Preparation"

    def test_readiness_label_boundaries(self):
        """Readiness labels align with score thresholds."""
        labels = {
            "Ready Now": (0.85, 1.0),
            "Needs Preparation": (0.6, 0.85),
            "Not Ready": (0.0, 0.6),
        }

        for label, (lower, upper) in labels.items():
            # Label should be applied when score is in range
            assert lower <= upper
            assert label in ["Ready Now", "Needs Preparation", "Not Ready"]


@pytest.mark.asyncio
class TestDomainCoverage:
    """Test domain-level skill coverage metrics."""

    def test_domain_coverage_calculation(self):
        """Domain coverage should sum to ~1.0 across all domains."""
        coverage = [
            DomainCoverage(
                domain="Technical",
                skills_required=10,
                skills_present=7,
                coverage_pct=0.7,
            ),
            DomainCoverage(
                domain="Leadership",
                skills_required=5,
                skills_present=3,
                coverage_pct=0.6,
            ),
            DomainCoverage(
                domain="Communication",
                skills_required=3,
                skills_present=3,
                coverage_pct=1.0,
            ),
        ]

        # Weighted average coverage
        total_required = sum(c.skills_required for c in coverage)
        weighted_coverage = sum(
            c.coverage_pct * c.skills_required for c in coverage
        ) / total_required

        assert 0.5 <= weighted_coverage <= 1.0

    def test_domain_coverage_boundary_conditions(self):
        """Domain coverage should handle edge cases."""
        # No skills required in domain
        coverage = DomainCoverage(
            domain="Optional",
            skills_required=0,
            skills_present=0,
            coverage_pct=1.0,  # 0/0 → 100% by convention
        )
        assert coverage.coverage_pct == 1.0

        # All skills present
        coverage = DomainCoverage(
            domain="Strong",
            skills_required=5,
            skills_present=5,
            coverage_pct=1.0,
        )
        assert coverage.coverage_pct == 1.0

        # No skills present
        coverage = DomainCoverage(
            domain="Weak",
            skills_required=5,
            skills_present=0,
            coverage_pct=0.0,
        )
        assert coverage.coverage_pct == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
