import numpy as np

from engines.normalization.normalization_engine import (
    SkillNormalizationEngine,
    SkillOntology,
)


def _build_ontology():
    return SkillOntology(
        [
            {
                "skill_id": "python",
                "canonical_name": "Python",
                "aliases": ["py"],
                "domain": "technical",
                "difficulty_level": "intermediate",
                "avg_time_to_learn_hours": 40,
                "importance_score": 0.9,
                "prerequisites": [],
                "onet_code": "x",
            },
            {
                "skill_id": "javascript",
                "canonical_name": "JavaScript",
                "aliases": ["js"],
                "domain": "technical",
                "difficulty_level": "intermediate",
                "avg_time_to_learn_hours": 50,
                "importance_score": 0.85,
                "prerequisites": [],
                "onet_code": "y",
            },
        ]
    )


def test_normalize_skill_exact_alias_match(monkeypatch):
    engine = SkillNormalizationEngine()
    ontology = _build_ontology()

    monkeypatch.setattr(engine, "_load_ontology", lambda: ontology)

    skill_id, confidence = engine.normalize_skill("py")

    assert skill_id == "python"
    assert confidence == 1.0


def test_normalize_skill_semantic_match_and_custom_fallback(monkeypatch):
    engine = SkillNormalizationEngine()
    engine._threshold = 0.82
    ontology = _build_ontology()

    class DummyModel:
        def encode(self, texts, **kwargs):
            value = texts[0].lower()
            if "javascrip" in value:
                return np.array([[1.0, 0.0]], dtype=np.float32)
            return np.array([[0.1, 0.1]], dtype=np.float32)

    monkeypatch.setattr(engine, "_load_ontology", lambda: ontology)
    monkeypatch.setattr(engine, "_load_model", lambda: DummyModel())
    monkeypatch.setattr(
        engine,
        "_load_ontology_embeddings",
        lambda: np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )

    semantic_id, semantic_conf = engine.normalize_skill("Javascrip")
    fallback_id, fallback_conf = engine.normalize_skill("TotallyUnknownSkill")

    assert semantic_id == "python"
    assert semantic_conf >= engine._threshold

    assert fallback_id == "custom_totallyunknownskill"
    assert fallback_conf < engine._threshold


def test_normalize_skill_list_deduplicates_by_higher_confidence(monkeypatch):
    engine = SkillNormalizationEngine()

    def fake_normalize(name, domain_hint=None):
        if name == "Python":
            return "python", 0.70
        if name == "Py":
            return "python", 0.95
        return "custom_other", 0.2

    monkeypatch.setattr(engine, "normalize_skill", fake_normalize)

    result = engine.normalize_skill_list(
        [
            {"name": "Python", "domain": "technical"},
            {"name": "Py", "domain": "technical"},
        ]
    )

    assert len(result) == 1
    assert result[0]["canonical_skill_id"] == "python"
    assert result[0]["normalization_confidence"] == 0.95
    assert result[0]["name"] == "Py"
