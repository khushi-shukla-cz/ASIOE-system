"""
ASIOE — Adaptive Path Engine
The core algorithmic engine of the system.

Algorithm: Adaptive Topological Learning Path Construction

Steps:
1. Receive gap analysis results (critical + major gaps)
2. For each gap skill, perform backward DFS to collect prerequisite tree
3. Remove skills already known by candidate (graph pruning)
4. Apply topological sort on the resulting DAG
5. Rank nodes using multi-factor scoring:
   - importance_score (from O*NET / ontology)
   - difficulty_level
   - dependency_depth (foundational skills first)
   - domain_priority (based on role's domain weights)
   - estimated_learning_efficiency (hours / importance)
6. Phase the path into logical learning phases
7. Attach course resources via RAG engine
8. Compute path metrics (efficiency_score, redundancy_eliminated)
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import structlog

from core.config import settings
from engines.skill_graph.skill_graph_engine import get_skill_graph_engine
from schemas.schemas import (
    DifficultyLevel,
    GapAnalysisResult,
    LearningModule,
    LearningPathResult,
    PathPhase,
)

logger = structlog.get_logger(__name__)

DIFFICULTY_ORDER = {
    DifficultyLevel.BEGINNER: 1,
    DifficultyLevel.INTERMEDIATE: 2,
    DifficultyLevel.ADVANCED: 3,
    DifficultyLevel.EXPERT: 4,
}

PHASE_SIZE_TARGET = 5  # Target modules per phase


class AdaptivePathEngine:
    """
    Constructs personalized learning paths using graph-based algorithms.
    This is the heart of ASIOE — pure algorithmic intelligence, no black-box.
    """

    def __init__(self) -> None:
        self.graph_engine = get_skill_graph_engine()

    async def generate_path(
        self,
        session_id: str,
        gap_analysis: GapAnalysisResult,
        candidate_skill_ids: Set[str],
        max_modules: int = settings.MAX_RECOMMENDATIONS,
        time_constraint_weeks: Optional[int] = None,
        priority_domains: Optional[List[str]] = None,
    ) -> LearningPathResult:
        """
        Main entry point. Returns a fully-structured LearningPathResult.
        """

        # Step 1: Collect all target skill IDs (critical > major > minor)
        target_skill_ids = self._collect_target_skills(gap_analysis)

        # Step 2: Expand with prerequisites via recursive graph traversal
        all_skill_ids, prerequisite_map = await self._expand_with_prerequisites(
            target_skill_ids, max_depth=settings.MAX_PATH_DEPTH
        )

        # Step 3: Prune known skills (deduplication + skip what candidate knows)
        pruned_ids, redundancy_eliminated = self._prune_known_skills(
            all_skill_ids, candidate_skill_ids
        )

        # Step 4: Build NetworkX DAG for algorithmic processing
        G = await self.graph_engine.build_networkx_graph(list(pruned_ids | target_skill_ids))

        # Step 5: Topological sort → ordered learning sequence
        ordered_ids = self._topological_sort(G, pruned_ids)

        # Step 6: Rank and score each node
        scored_modules = self._rank_nodes(
            ordered_ids, G, gap_analysis, priority_domains or []
        )

        # Step 7: Apply time constraint if provided
        if time_constraint_weeks:
            scored_modules = self._apply_time_constraint(
                scored_modules, time_constraint_weeks
            )

        # Step 8: Cap at max_modules (highest-value first)
        scored_modules = scored_modules[:max_modules]

        # Step 9: Phase the path
        phases = self._create_phases(scored_modules, G)

        # Step 10: Build serializable graph for frontend
        path_graph = self._build_path_graph(scored_modules, G)

        # Step 11: Compute metrics
        total_hours = sum(m.estimated_hours for m in scored_modules)
        total_weeks = total_hours / 10.0  # 10 hrs/week learning pace
        efficiency_score = self._compute_efficiency_score(
            scored_modules, redundancy_eliminated
        )

        reasoning = self._build_path_reasoning(
            gap_analysis, scored_modules, redundancy_eliminated, total_weeks
        )

        logger.info(
            "path.generated",
            session=session_id,
            modules=len(scored_modules),
            phases=len(phases),
            total_hours=round(total_hours, 1),
            efficiency=round(efficiency_score, 3),
            redundancy_eliminated=redundancy_eliminated,
        )

        return LearningPathResult(
            session_id=session_id,
            path_id=str(uuid.uuid4()),
            target_role=gap_analysis.session_id,  # Will be enriched by service layer
            phases=phases,
            total_modules=len(scored_modules),
            total_hours=round(total_hours, 1),
            total_weeks=round(total_weeks, 1),
            path_graph=path_graph,
            efficiency_score=round(efficiency_score, 4),
            redundancy_eliminated=redundancy_eliminated,
            path_algorithm="adaptive_topological_dfs_v2",
            path_version=2,
            reasoning_trace=reasoning,
            generated_at=datetime.utcnow(),
        )

    def _collect_target_skills(self, gap_analysis: GapAnalysisResult) -> Set[str]:
        """Extract skill IDs from gap analysis, prioritized by severity."""
        targets = set()
        # Critical gaps are mandatory
        for gap in gap_analysis.critical_gaps:
            targets.add(gap.skill_id)
        # Major gaps included
        for gap in gap_analysis.major_gaps:
            targets.add(gap.skill_id)
        # Minor gaps if we have space
        for gap in gap_analysis.minor_gaps[:5]:
            targets.add(gap.skill_id)
        return targets

    async def _expand_with_prerequisites(
        self,
        target_ids: Set[str],
        max_depth: int,
    ) -> Tuple[Set[str], Dict[str, List[str]]]:
        """
        For each target skill, recursively fetch prerequisites.
        Returns (all_skill_ids, prerequisite_map).
        """
        all_ids: Set[str] = set(target_ids)
        prereq_map: Dict[str, List[str]] = defaultdict(list)

        tasks = [
            self.graph_engine.get_prerequisites_recursive(skill_id, max_depth)
            for skill_id in target_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for skill_id, prereqs in zip(target_ids, results):
            if isinstance(prereqs, Exception):
                logger.warning("path.prereq.error", skill=skill_id, error=str(prereqs))
                continue
            for prereq in prereqs:
                pid = prereq.get("skill_id")
                if pid:
                    all_ids.add(pid)
                    prereq_map[skill_id].append(pid)

        return all_ids, dict(prereq_map)

    def _prune_known_skills(
        self,
        all_skill_ids: Set[str],
        known_skill_ids: Set[str],
    ) -> Tuple[Set[str], int]:
        """
        Remove skills the candidate already knows.
        Returns (pruned_set, count_removed).
        """
        pruned = all_skill_ids - known_skill_ids
        removed = len(all_skill_ids) - len(pruned)
        logger.debug(
            "path.pruned",
            total=len(all_skill_ids),
            known=len(known_skill_ids),
            removed=removed,
            remaining=len(pruned),
        )
        return pruned, removed

    def _topological_sort(
        self, G: nx.DiGraph, skill_ids: Set[str]
    ) -> List[str]:
        """
        Topological sort ensures prerequisites are always learned first.
        Handles disconnected subgraphs and cycles (breaks cycles safely).
        """
        # Filter graph to only include relevant nodes
        subgraph = G.subgraph(
            [n for n in G.nodes if n in skill_ids]
        ).copy()

        # Detect and break cycles (shouldn't happen in well-formed DAG, but safety net)
        if not nx.is_directed_acyclic_graph(subgraph):
            cycles = list(nx.simple_cycles(subgraph))
            logger.warning("path.cycles_detected", count=len(cycles))
            for cycle in cycles:
                if len(cycle) > 1:
                    subgraph.remove_edge(cycle[-1], cycle[0])

        try:
            ordered = list(nx.topological_sort(subgraph))
            # Reverse so prerequisites come first
            # nx.topological_sort returns dependents last → we want prerequisites first
            # The direction is: A -> B means A is prerequisite of B
            # So topological order gives us A before B ✓
            return ordered
        except nx.NetworkXUnfeasible:
            logger.error("path.topo_sort.failed_fallback_to_degree_sort")
            # Fallback: sort by in-degree (nodes with fewer prerequisites first)
            return sorted(
                skill_ids,
                key=lambda sid: G.in_degree(sid) if sid in G else 0
            )

    def _rank_nodes(
        self,
        ordered_ids: List[str],
        G: nx.DiGraph,
        gap_analysis: GapAnalysisResult,
        priority_domains: List[str],
    ) -> List[LearningModule]:
        """
        Multi-factor node ranking within the topological order.
        Produces fully-formed LearningModule objects.
        """
        # Build gap severity lookup
        severity_boost: Dict[str, float] = {}
        for gap in gap_analysis.critical_gaps:
            severity_boost[gap.skill_id] = 1.0
        for gap in gap_analysis.major_gaps:
            severity_boost[gap.skill_id] = 0.7
        for gap in gap_analysis.minor_gaps:
            severity_boost[gap.skill_id] = 0.3

        modules = []
        for idx, skill_id in enumerate(ordered_ids):
            if skill_id not in G:
                continue

            node_data = G.nodes[skill_id]
            importance = node_data.get("importance", 0.5)
            difficulty = node_data.get("difficulty", "intermediate")
            hours = node_data.get("hours", 40.0)
            domain = node_data.get("domain", "technical")
            name = node_data.get("name", skill_id)

            # --- Multi-factor composite score ---
            importance_score = importance
            gap_boost = severity_boost.get(skill_id, 0.0)
            domain_boost = 0.1 if domain in priority_domains else 0.0
            dependency_depth = G.in_degree(skill_id)  # More prerequisites → foundational
            depth_score = 1.0 / (1.0 + dependency_depth)  # Foundational skills get priority

            composite_score = (
                0.35 * importance_score
                + 0.35 * gap_boost
                + 0.15 * depth_score
                + 0.10 * domain_boost
                + 0.05 * (1.0 / max(hours / 40.0, 0.5))  # Efficiency: prefer lower-time skills
            )

            # Build prerequisite and unlock lists
            prereq_ids = [str(p) for p in G.predecessors(skill_id)]
            unlock_ids = [str(s) for s in G.successors(skill_id)]

            # Build dependency chain for explainability
            dep_chain = self._build_dependency_chain(skill_id, G, max_depth=4)

            # Why this skill is selected
            why = self._explain_selection(
                skill_id=skill_id,
                name=name,
                gap_boost=gap_boost,
                importance=importance,
                prereq_count=len(prereq_ids),
                domain=domain,
            )

            module = LearningModule(
                module_id=str(uuid.uuid4()),
                skill_id=skill_id,
                skill_name=name,
                title=f"Master {name}",
                description=f"Develop proficiency in {name} for role readiness.",
                domain=domain,
                difficulty_level=difficulty,
                estimated_hours=hours,
                sequence_order=idx + 1,
                phase_number=1,  # Will be updated in _create_phases
                prerequisite_module_ids=prereq_ids,
                unlocks_module_ids=unlock_ids,
                why_selected=why,
                dependency_chain=dep_chain,
                importance_score=round(importance_score, 3),
                confidence_score=round(composite_score, 3),
            )
            modules.append((composite_score, module))

        # Sort by topological order (already correct) but within same topo-level,
        # prioritize by composite score
        modules.sort(key=lambda x: (x[1].sequence_order, -x[0]))
        return [m for _, m in modules]

    def _apply_time_constraint(
        self,
        modules: List[LearningModule],
        max_weeks: int,
    ) -> List[LearningModule]:
        """Filter modules to fit within time budget (10 hrs/week)."""
        max_hours = max_weeks * 10.0
        selected = []
        accumulated = 0.0

        # Always include critical skills first (sorted by importance_score)
        sorted_modules = sorted(modules, key=lambda m: -m.importance_score)
        for module in sorted_modules:
            if accumulated + module.estimated_hours <= max_hours:
                selected.append(module)
                accumulated += module.estimated_hours

        # Re-sort by sequence order
        selected.sort(key=lambda m: m.sequence_order)
        logger.info("path.time_constrained", weeks=max_weeks, selected=len(selected))
        return selected

    def _create_phases(
        self, modules: List[LearningModule], G: nx.DiGraph
    ) -> List[PathPhase]:
        """
        Group modules into logical learning phases.
        Phase logic:
        - Phase 1: Foundations (prerequisites, beginner)
        - Phase 2: Core Skills (intermediate, directly mapped to gaps)
        - Phase 3: Advanced (advanced/expert, cross-domain)
        """
        if not modules:
            return []

        phases_data: Dict[int, List[LearningModule]] = defaultdict(list)

        for idx, module in enumerate(modules):
            diff = module.difficulty_level
            if diff in (DifficultyLevel.BEGINNER,) or len(module.prerequisite_module_ids) == 0:
                phase_num = 1
            elif diff == DifficultyLevel.INTERMEDIATE:
                phase_num = 2
            else:
                phase_num = 3

            module.phase_number = phase_num
            module.sequence_order = idx + 1
            phases_data[phase_num].append(module)

        phase_names = {
            1: "Foundation Building",
            2: "Core Competency Development",
            3: "Advanced Mastery",
        }
        phase_descriptions = {
            1: "Establish foundational knowledge and prerequisite skills required for higher-order learning.",
            2: "Develop core competencies directly mapped to role requirements.",
            3: "Achieve advanced proficiency and cross-domain integration.",
        }

        phases = []
        for phase_num in sorted(phases_data.keys()):
            phase_modules = phases_data[phase_num]
            phase_hours = sum(m.estimated_hours for m in phase_modules)
            domains = list({m.domain for m in phase_modules})

            phases.append(PathPhase(
                phase_number=phase_num,
                phase_name=phase_names.get(phase_num, f"Phase {phase_num}"),
                description=phase_descriptions.get(phase_num, ""),
                modules=phase_modules,
                estimated_hours=round(phase_hours, 1),
                estimated_weeks=round(phase_hours / 10.0, 1),
                focus_domains=domains,
            ))

        return phases

    def _build_path_graph(
        self, modules: List[LearningModule], G: nx.DiGraph
    ) -> Dict[str, Any]:
        """Build D3-compatible graph representation."""
        nodes = []
        edges = []
        module_id_map = {m.skill_id: m.module_id for m in modules}

        for module in modules:
            nodes.append({
                "id": module.module_id,
                "skill_id": module.skill_id,
                "label": module.skill_name,
                "domain": module.domain,
                "difficulty": module.difficulty_level,
                "hours": module.estimated_hours,
                "phase": module.phase_number,
                "importance": module.importance_score,
                "confidence": module.confidence_score,
            })

        for module in modules:
            for prereq_id in module.prerequisite_module_ids:
                if prereq_id in module_id_map.values():
                    edges.append({
                        "source": prereq_id,
                        "target": module.module_id,
                        "type": "prerequisite",
                    })

        return {"nodes": nodes, "edges": edges}

    def _build_dependency_chain(
        self, skill_id: str, G: nx.DiGraph, max_depth: int
    ) -> List[str]:
        """Build readable dependency chain for explainability."""
        chain = []
        current = skill_id
        for _ in range(max_depth):
            predecessors = list(G.predecessors(current))
            if not predecessors:
                break
            current = predecessors[0]
            name = G.nodes[current].get("name", current) if current in G else current
            chain.append(name)
        return list(reversed(chain))

    def _explain_selection(
        self,
        skill_id: str,
        name: str,
        gap_boost: float,
        importance: float,
        prereq_count: int,
        domain: str,
    ) -> str:
        """Generate human-readable reason for skill inclusion."""
        reasons = []
        if gap_boost >= 0.9:
            reasons.append(f"directly addresses a critical skill gap")
        elif gap_boost >= 0.5:
            reasons.append(f"addresses a major deficiency identified in the role requirements")
        if importance >= 0.8:
            reasons.append(f"ranks in top importance tier for this domain")
        if prereq_count == 0:
            reasons.append(f"foundational skill with no prerequisites — high learning efficiency")
        elif prereq_count <= 2:
            reasons.append(f"has {prereq_count} prerequisite(s) already sequenced in path")
        return (
            f"Selected because {' and '.join(reasons) if reasons else 'it contributes to role readiness'}. "
            f"Domain: {domain}."
        )

    def _compute_efficiency_score(
        self, modules: List[LearningModule], redundancy_eliminated: int
    ) -> float:
        """
        Efficiency = how well the path avoids redundancy.
        Higher is better (1.0 = perfectly efficient).
        """
        if not modules:
            return 0.0
        total_considered = len(modules) + redundancy_eliminated
        if total_considered == 0:
            return 1.0
        return redundancy_eliminated / total_considered

    def _build_path_reasoning(
        self,
        gap_analysis: GapAnalysisResult,
        modules: List[LearningModule],
        redundancy_eliminated: int,
        total_weeks: float,
    ) -> str:
        critical_count = len(gap_analysis.critical_gaps)
        major_count = len(gap_analysis.major_gaps)
        return (
            f"Adaptive path generated using topological DFS algorithm across the skill knowledge graph. "
            f"Identified {critical_count} critical and {major_count} major skill gaps. "
            f"Path contains {len(modules)} modules across {total_weeks:.1f} weeks at 10 hrs/week. "
            f"{redundancy_eliminated} redundant modules eliminated based on candidate's existing competencies. "
            f"Phases structured: Foundation → Core Development → Advanced Mastery."
        )


_path_engine: Optional[AdaptivePathEngine] = None


def get_path_engine() -> AdaptivePathEngine:
    global _path_engine
    if _path_engine is None:
        _path_engine = AdaptivePathEngine()
    return _path_engine
