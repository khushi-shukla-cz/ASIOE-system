from engines.parsing.parsing_engine import ParsingEngine


def test_validate_resume_extraction_normalizes_invalid_fields():
    engine = object.__new__(ParsingEngine)

    raw = {
        "skills": [
            {
                "name": "Python",
                "domain": "invalid_domain",
                "proficiency_level": "wizard",
                "proficiency_score": 1.8,
                "confidence": -0.5,
            },
            {
                "name": "",
                "domain": "technical",
                "proficiency_level": "beginner",
                "proficiency_score": 0.2,
                "confidence": 0.9,
            },
        ],
        "parsing_confidence": 0.99,
    }

    result = engine._validate_resume_extraction(raw, extraction_conf=0.9)

    assert len(result["skills"]) == 1
    skill = result["skills"][0]
    assert skill["domain"] == "technical"
    assert skill["proficiency_level"] == "intermediate"
    assert skill["proficiency_score"] == 1.0
    assert skill["confidence"] == 0.0
    assert result["parsing_confidence"] == 0.9


def test_validate_jd_extraction_filters_empty_and_clamps_scores():
    engine = object.__new__(ParsingEngine)

    raw = {
        "required_skills": [
            {
                "name": "SQL",
                "domain": "unknown",
                "proficiency_score": 2.0,
                "confidence": -1.0,
            },
            {
                "name": "",
                "domain": "technical",
                "proficiency_score": 0.5,
                "confidence": 0.8,
            },
        ],
        "preferred_skills": [
            {
                "name": "Communication",
                "domain": "communication",
                "proficiency_score": -0.2,
                "confidence": 1.5,
            }
        ],
    }

    result = engine._validate_jd_extraction(raw)

    assert len(result["required_skills"]) == 1
    assert result["required_skills"][0]["domain"] == "technical"
    assert result["required_skills"][0]["proficiency_score"] == 1.0
    assert result["required_skills"][0]["confidence"] == 0.0

    assert len(result["preferred_skills"]) == 1
    assert result["preferred_skills"][0]["domain"] == "communication"
    assert result["preferred_skills"][0]["proficiency_score"] == 0.0
    assert result["preferred_skills"][0]["confidence"] == 1.0
