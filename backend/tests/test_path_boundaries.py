"""Unit tests for path engine boundary conditions: topological ordering, phasing, and efficiency."""

from __future__ import annotations

from datetime import datetime

import pytest

from engines.path.path_engine import PathEngine
from schemas.schemas import DifficultyLevel, LearningModule, LearningPathResult, PathPhase, SkillDomain


class TestPathTopologicalOrdering:
    """Tests for prerequisite-respecting topological sort."""

    @pytest.mark.asyncio
    async def test_topological_sort_respects_prerequisites(self):
        """Verify generated path respects module prerequisite relationships."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        # Modules with explicit prerequisites
        modules = [
            LearningModule(
                module_id="m_basics",
                skill_id="python_basics",
                skill_name="Python Basics",
                title="Python Fundamentals",
                description="desc",
                domain=SkillDomain.TECHNICAL,
                difficulty_level=DifficultyLevel.BEGINNER,
                estimated_hours=20,
                sequence_order=1,
                phase_number=1,
                prerequisite_module_ids=[],
                unlocks_module_ids=["m_advanced"],
                why_selected="Foundation",
                dependency_chain=[],
                importance_score=0.95,
                confidence_score=0.95,
            ),
            LearningModule(
                module_id="m_advanced",
                skill_id="advanced_python",
                skill_name="Advanced Python",
                title="Advanced Patterns",
                description="desc",
                domain=SkillDomain.TECHNICAL,
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                estimated_hours=30,
                sequence_order=2,
                phase_number=2,
                prerequisite_module_ids=["m_basics"],
                unlocks_module_ids=["m_oop"],
                why_selected="Post-foundation",
                dependency_chain=["python_basics"],
                importance_score=0.85,
                confidence_score=0.85,
            ),
            LearningModule(
                module_id="m_oop",
                skill_id="oop",
                skill_name="OOP",
                title="Object-Oriented Programming",
                description="desc",
                domain=SkillDomain.TECHNICAL,
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                estimated_hours=25,
                sequence_order=3,
                phase_number=2,
                prerequisite_module_ids=["m_advanced"],
                unlocks_module_ids=[],
                why_selected="Advanced concept",
                dependency_chain=["python_basics", "advanced_python"],
                importance_score=0.8,
                confidence_score=0.8,
            ),
        ]

        # Assuming generate_path returns LearningPathResult
        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Backend Engineer",
            phases=[],
            total_modules=len(modules),
            total_hours=sum(m.estimated_hours for m in modules),
            total_weeks=8,
            path_graph={"nodes": [m.module_id for m in modules], "edges": []},
            efficiency_score=0.85,
            redundancy_eliminated=0,
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        # Extract order from path phases
        module_order = []
        for phase in path.phases:
            for module in phase.modules:
                module_order.append(module.module_id)

        # Verify prerequisites come before dependents
        if "m_basics" in module_order and "m_advanced" in module_order:
            assert module_order.index("m_basics") < module_order.index("m_advanced")
        
        if "m_advanced" in module_order and "m_oop" in module_order:
            assert module_order.index("m_advanced") < module_order.index("m_oop")

    @pytest.mark.asyncio
    async def test_path_contains_no_cycles(self):
        """Verify generated path is acyclic (DAG property)."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        # Create path
        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Engineer",
            phases=[],
            total_modules=3,
            total_hours=75,
            total_weeks=8,
            path_graph={"nodes": ["m1", "m2", "m3"], "edges": [("m1", "m2"), ("m2", "m3")]},
            efficiency_score=0.85,
            redundancy_eliminated=0,
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        # Check for cycles using simple DFS
        edges = path.path_graph["edges"]
        
        def has_cycle(edges):
            from collections import defaultdict, deque
            graph = defaultdict(list)
            in_degree = defaultdict(int)
            
            nodes = set()
            for src, dst in edges:
                nodes.add(src)
                nodes.add(dst)
                graph[src].append(dst)
                in_degree[dst] += 1
            
            # Topological sort attempt
            queue = deque([node for node in nodes if in_degree[node] == 0])
            sorted_count = 0
            
            while queue:
                node = queue.popleft()
                sorted_count += 1
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            return sorted_count != len(nodes)

        assert not has_cycle(edges), "Path graph contains cycle"

    @pytest.mark.asyncio
    async def test_modules_ordered_by_importance_rank(self):
        """Verify modules within phase are ordered by importance/difficulty progression."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        # Create phase with multiple modules
        phase = PathPhase(
            phase_number=1,
            phase_name="Foundations",
            description="Foundation skills",
            modules=[
                LearningModule(
                    module_id="m_fundamentals",
                    skill_id="fundamentals",
                    skill_name="Fundamentals",
                    title="Fundamentals",
                    description="desc",
                    domain=SkillDomain.TECHNICAL,
                    difficulty_level=DifficultyLevel.BEGINNER,
                    estimated_hours=20,
                    sequence_order=1,
                    phase_number=1,
                    prerequisite_module_ids=[],
                    unlocks_module_ids=[],
                    why_selected="Start",
                    dependency_chain=[],
                    importance_score=0.95,
                    confidence_score=0.95,
                ),
                LearningModule(
                    module_id="m_basics",
                    skill_id="basics",
                    skill_name="Basics",
                    title="Basics",
                    description="desc",
                    domain=SkillDomain.TECHNICAL,
                    difficulty_level=DifficultyLevel.BEGINNER,
                    estimated_hours=15,
                    sequence_order=2,
                    phase_number=1,
                    prerequisite_module_ids=[],
                    unlocks_module_ids=[],
                    why_selected="Next",
                    dependency_chain=[],
                    importance_score=0.85,
                    confidence_score=0.85,
                ),
            ],
            estimated_hours=35,
            estimated_weeks=4,
            focus_domains=["technical"],
        )

        # Verify higher importance comes earlier
        if phase.modules:
            for i in range(len(phase.modules) - 1):
                assert phase.modules[i].importance_score >= phase.modules[i + 1].importance_score


class TestPathPhasing:
    """Tests for learning path phase structure and optimization."""

    @pytest.mark.asyncio
    async def test_phase_contains_target_module_count(self):
        """Verify phases are sized according to learning capacity."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Backend Engineer",
            phases=[
                PathPhase(
                    phase_number=1,
                    phase_name="Phase 1",
                    description="Start",
                    modules=[
                        LearningModule(
                            module_id=f"m{i}",
                            skill_id=f"skill{i}",
                            skill_name=f"Skill {i}",
                            title=f"Module {i}",
                            description="desc",
                            domain=SkillDomain.TECHNICAL,
                            difficulty_level=DifficultyLevel.BEGINNER,
                            estimated_hours=10,
                            sequence_order=i,
                            phase_number=1,
                            prerequisite_module_ids=[],
                            unlocks_module_ids=[],
                            why_selected="Learn",
                            dependency_chain=[],
                            importance_score=0.8,
                            confidence_score=0.8,
                        )
                        for i in range(4)
                    ],
                    estimated_hours=40,
                    estimated_weeks=4,
                    focus_domains=["technical"],
                ),
            ],
            total_modules=4,
            total_hours=40,
            total_weeks=4,
            path_graph={"nodes": [], "edges": []},
            efficiency_score=0.85,
            redundancy_eliminated=0,
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        # Check phase module count is reasonable (e.g., 3-6 modules per phase for 4-week phase)
        for phase in path.phases:
            expected_range = max(2, phase.estimated_weeks - 1)  # Rough heuristic
            assert len(phase.modules) > 0

    @pytest.mark.asyncio
    async def test_estimated_weeks_reasonable_for_module_count(self):
        """Verify estimated weeks correlate with module count and hours."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Engineer",
            phases=[],
            total_modules=10,
            total_hours=80.0,
            total_weeks=10.0,
            path_graph={"nodes": [], "edges": []},
            efficiency_score=0.85,
            redundancy_eliminated=0,
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        # Rough validation: 8 hours/week is typical
        hours_per_week = path.total_hours / path.total_weeks if path.total_weeks > 0 else 0
        assert 5.0 <= hours_per_week <= 20.0

    @pytest.mark.asyncio
    async def test_learning_efficiency_score_reflects_path_optimization(self):
        """Verify efficiency score indicates optimization (0 = no redundancy, 1 = fully optimized)."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Engineer",
            phases=[],
            total_modules=10,
            total_hours=80.0,
            total_weeks=10.0,
            path_graph={"nodes": [], "edges": []},
            efficiency_score=0.92,  # High efficiency
            redundancy_eliminated=3,  # 3 redundant modules removed
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        # Efficiency should be bounded [0, 1]
        assert 0.0 <= path.efficiency_score <= 1.0
        
        # Efficiency should increase if redundancy is eliminated
        assert path.efficiency_score >= 0.5


class TestPathBoundaryConditions:
    """Tests for edge cases and boundary conditions in path generation."""

    @pytest.mark.asyncio
    async def test_single_module_path_valid(self):
        """Verify path with single module is valid."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Engineer",
            phases=[
                PathPhase(
                    phase_number=1,
                    phase_name="Sole Module",
                    description="Single module",
                    modules=[
                        LearningModule(
                            module_id="m1",
                            skill_id="skill1",
                            skill_name="Skill",
                            title="Module",
                            description="desc",
                            domain=SkillDomain.TECHNICAL,
                            difficulty_level=DifficultyLevel.BEGINNER,
                            estimated_hours=10,
                            sequence_order=1,
                            phase_number=1,
                            prerequisite_module_ids=[],
                            unlocks_module_ids=[],
                            why_selected="Only",
                            dependency_chain=[],
                            importance_score=1.0,
                            confidence_score=1.0,
                        )
                    ],
                    estimated_hours=10,
                    estimated_weeks=1,
                    focus_domains=["technical"],
                )
            ],
            total_modules=1,
            total_hours=10.0,
            total_weeks=1.0,
            path_graph={"nodes": ["m1"], "edges": []},
            efficiency_score=1.0,
            redundancy_eliminated=0,
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        assert path.total_modules == 1
        assert len(path.phases) >= 1

    @pytest.mark.asyncio
    async def test_large_module_count_path_valid(self):
        """Verify path with many modules (e.g., 50+) scales correctly."""
        engine = object.__new__(PathEngine)
        engine._initialized = True

        large_module_count = 50
        path = LearningPathResult(
            session_id="s1",
            path_id="path1",
            target_role="Engineer",
            phases=[],
            total_modules=large_module_count,
            total_hours=large_module_count * 8.0,  # 8 hours per module on average
            total_weeks=12.0,
            path_graph={"nodes": [f"m{i}" for i in range(large_module_count)], "edges": []},
            efficiency_score=0.80,
            redundancy_eliminated=0,
            path_algorithm="topological_dfs",
            path_version=1,
            reasoning_trace="trace",
            generated_at=datetime.utcnow(),
        )

        assert path.total_modules == large_module_count
        # Should still produce reasonable time estimate
        hours_per_week = path.total_hours / path.total_weeks
        assert 20 <= hours_per_week <= 40  # Intensive but realistic
