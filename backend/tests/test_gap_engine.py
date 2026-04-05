from engines.gap.gap_engine import GapAnalysisEngine
from schemas.schemas import DomainCoverage


def test_classify_gaps_into_critical_major_minor():
    engine = GapAnalysisEngine()
    gaps = [
        {
            "skill_id": "s1",
            "skill_name": "Critical Skill",
            "domain": "technical",
            "current_score": 0.1,
            "required_score": 0.9,
            "gap_delta": 0.8,
        },
        {
            "skill_id": "s2",
            "skill_name": "Major Skill",
            "domain": "analytical",
            "current_score": 0.3,
            "required_score": 0.7,
            "gap_delta": 0.4,
        },
        {
            "skill_id": "s3",
            "skill_name": "Minor Skill",
            "domain": "communication",
            "current_score": 0.6,
            "required_score": 0.8,
            "gap_delta": 0.2,
        },
    ]

    critical, major, minor = engine._classify_gaps(gaps)

    assert len(critical) == 1
    assert len(major) == 1
    assert len(minor) == 1
    assert critical[0].severity.value == "critical"
    assert major[0].severity.value == "major"
    assert minor[0].severity.value == "minor"


def test_compute_readiness_score_applies_weight_and_penalties():
    engine = GapAnalysisEngine()

    # Base score resolves to 1.0 here since all covered domains have radar_value=1.0.
    domain_coverage = [
        DomainCoverage(
            domain="technical",
            coverage_percentage=100.0,
            matched_skills=4,
            total_required=4,
            radar_value=1.0,
        ),
        DomainCoverage(
            domain="analytical",
            coverage_percentage=100.0,
            matched_skills=2,
            total_required=2,
            radar_value=1.0,
        ),
    ]

    # penalty = 2*0.08 + 3*0.03 = 0.25 -> final 0.75
    score = engine._compute_readiness_score(
        domain_coverage=domain_coverage,
        critical_gaps=[object(), object()],
        major_gaps=[object(), object(), object()],
    )

    assert score == 0.75


def test_compute_readiness_score_never_goes_below_zero():
    engine = GapAnalysisEngine()
    domain_coverage = [
        DomainCoverage(
            domain="technical",
            coverage_percentage=10.0,
            matched_skills=1,
            total_required=10,
            radar_value=0.1,
        )
    ]

    score = engine._compute_readiness_score(
        domain_coverage=domain_coverage,
        critical_gaps=[object()] * 10,
        major_gaps=[object()] * 10,
    )

    assert score == 0.0
