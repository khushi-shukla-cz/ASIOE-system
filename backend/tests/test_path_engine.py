import sys

import networkx as nx

# If another test inserted a lightweight module stub, discard it so this unit
# test imports the real implementation.
existing = sys.modules.get("engines.path.path_engine")
if existing is not None and not getattr(existing, "__file__", None):
    del sys.modules["engines.path.path_engine"]

from engines.path.path_engine import AdaptivePathEngine
from schemas.schemas import GapSeverity, SkillGap


class _DummyGapAnalysis:
    def __init__(self):
        self.critical_gaps = [
            SkillGap(
                skill_id="skill_b",
                skill_name="Skill B",
                domain="technical",
                severity=GapSeverity.CRITICAL,
                current_score=0.1,
                required_score=0.9,
                gap_delta=0.8,
                reasoning="critical",
            )
        ]
        self.major_gaps = [
            SkillGap(
                skill_id="skill_c",
                skill_name="Skill C",
                domain="technical",
                severity=GapSeverity.MAJOR,
                current_score=0.3,
                required_score=0.7,
                gap_delta=0.4,
                reasoning="major",
            )
        ]
        self.minor_gaps = []


def test_rank_nodes_scores_and_sequences_modules():
    engine = AdaptivePathEngine()
    gap_analysis = _DummyGapAnalysis()

    graph = nx.DiGraph()
    graph.add_node(
        "skill_a",
        name="Skill A",
        domain="technical",
        difficulty="beginner",
        hours=20.0,
        importance=0.7,
    )
    graph.add_node(
        "skill_b",
        name="Skill B",
        domain="technical",
        difficulty="intermediate",
        hours=20.0,
        importance=0.7,
    )
    graph.add_node(
        "skill_c",
        name="Skill C",
        domain="technical",
        difficulty="intermediate",
        hours=20.0,
        importance=0.7,
    )

    # skill_a is prerequisite of skill_b, so skill_a has no prerequisites.
    graph.add_edge("skill_a", "skill_b")

    ordered_ids = ["skill_a", "skill_b", "skill_c"]
    modules = engine._rank_nodes(
        ordered_ids=ordered_ids,
        G=graph,
        gap_analysis=gap_analysis,
        priority_domains=["technical"],
    )

    assert [m.skill_id for m in modules] == ordered_ids
    assert [m.sequence_order for m in modules] == [1, 2, 3]

    by_id = {m.skill_id: m for m in modules}

    # Critical gap boost should rank confidence higher than major boost when other factors match.
    assert by_id["skill_b"].confidence_score > by_id["skill_c"].confidence_score

    # Foundational node with no prerequisites should include that reason.
    assert "foundational skill with no prerequisites" in by_id["skill_a"].why_selected


def test_topological_sort_handles_cycle_by_breaking_edge(monkeypatch):
    engine = AdaptivePathEngine()

    graph = nx.DiGraph()
    graph.add_node("skill_a")
    graph.add_node("skill_b")
    graph.add_edge("skill_a", "skill_b")
    graph.add_edge("skill_b", "skill_a")

    # Force deterministic cycle order to verify safe cycle edge removal behavior.
    monkeypatch.setattr(nx, "simple_cycles", lambda _g: [["skill_a", "skill_b"]])

    ordered = engine._topological_sort(graph, {"skill_a", "skill_b"})

    assert ordered == ["skill_a", "skill_b"]
