"""
ASIOE — Skill Graph Engine
Manages the Neo4j-backed Directed Acyclic Graph (DAG) of skills.

Graph Schema:
  Nodes:
    (:Skill)  — atomic competency unit
    (:Domain) — knowledge domain grouping
    (:Role)   — target job role
    (:Course) — learning resource

  Edges:
    [:PREREQUISITE_OF]  — skill A must be learned before skill B
    [:RELATED_TO]       — semantic similarity (bidirectional)
    [:BELONGS_TO]       — skill belongs to domain
    [:REQUIRED_FOR]     — skill required for role
    [:TEACHES]          — course teaches skill
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import structlog

from db.neo4j_manager import neo4j_manager

logger = structlog.get_logger(__name__)


# ── Cypher Query Library ───────────────────────────────────────────────────────

class CypherQueries:

    CREATE_SKILL = """
    MERGE (s:Skill {skill_id: $skill_id})
    SET s.name = $name,
        s.canonical_name = $canonical_name,
        s.domain = $domain,
        s.difficulty_level = $difficulty_level,
        s.avg_time_to_learn_hours = $avg_time_to_learn_hours,
        s.importance_score = $importance_score,
        s.onet_code = $onet_code,
        s.updated_at = datetime()
    RETURN s
    """

    CREATE_PREREQUISITE = """
    MATCH (a:Skill {skill_id: $from_skill_id})
    MATCH (b:Skill {skill_id: $to_skill_id})
    MERGE (a)-[r:PREREQUISITE_OF]->(b)
    SET r.strength = $strength
    RETURN r
    """

    CREATE_RELATED = """
    MATCH (a:Skill {skill_id: $skill_id_a})
    MATCH (b:Skill {skill_id: $skill_id_b})
    MERGE (a)-[r:RELATED_TO]-(b)
    SET r.similarity_score = $similarity
    RETURN r
    """

    GET_SKILL = """
    MATCH (s:Skill {skill_id: $skill_id})
    OPTIONAL MATCH (s)-[:PREREQUISITE_OF]->(dep:Skill)
    RETURN s, collect(dep.skill_id) as prerequisites
    """

    GET_PREREQUISITES_RECURSIVE = """
    MATCH path = (ancestor:Skill)-[:PREREQUISITE_OF*1..{depth}]->(target:Skill {{skill_id: $skill_id}})
    RETURN DISTINCT ancestor.skill_id as skill_id,
                   ancestor.name as name,
                   ancestor.domain as domain,
                   ancestor.difficulty_level as difficulty,
                   ancestor.avg_time_to_learn_hours as hours,
                   ancestor.importance_score as importance,
                   length(path) as depth
    ORDER BY depth ASC
    """

    GET_SKILLS_FOR_ROLE = """
    MATCH (r:Role {role_id: $role_id})-[:REQUIRED_FOR]-(s:Skill)
    RETURN s.skill_id as skill_id, s.name as name,
           s.domain as domain, s.importance_score as importance
    ORDER BY importance DESC
    """

    GET_ALL_SKILLS_SUBGRAPH = """
    MATCH (s:Skill)
    WHERE s.skill_id IN $skill_ids
    OPTIONAL MATCH (s)-[r:PREREQUISITE_OF]->(t:Skill)
    WHERE t.skill_id IN $skill_ids
    RETURN s, collect({to: t.skill_id, strength: r.strength}) as edges
    """

    SKILLS_COUNT = "MATCH (s:Skill) RETURN count(s) as count"

    GET_RELATED_SKILLS = """
    MATCH (s:Skill {skill_id: $skill_id})-[r:RELATED_TO]-(related:Skill)
    WHERE r.similarity_score >= $threshold
    RETURN related.skill_id as skill_id, related.name as name,
           r.similarity_score as similarity
    ORDER BY similarity DESC
    LIMIT $limit
    """


class SkillGraphEngine:
    """
    Manages the skill knowledge graph in Neo4j.
    Provides graph query APIs used by Gap and Path engines.
    """

    async def initialize_graph(self, ontology_path: Path) -> int:
        """
        Seed Neo4j from the ontology JSON file.
        Idempotent — uses MERGE to avoid duplicates.
        Returns number of skills loaded.
        """
        if not ontology_path.exists():
            logger.warning("graph.seed.missing_ontology")
            return 0

        with open(ontology_path) as f:
            skills = json.load(f)

        # Batch-load skills
        loaded = 0
        for skill in skills:
            await neo4j_manager.run_query(
                CypherQueries.CREATE_SKILL,
                {
                    "skill_id": skill["skill_id"],
                    "name": skill["canonical_name"],
                    "canonical_name": skill["canonical_name"],
                    "domain": skill.get("domain", "technical"),
                    "difficulty_level": skill.get("difficulty_level", "intermediate"),
                    "avg_time_to_learn_hours": skill.get("avg_time_to_learn_hours", 40),
                    "importance_score": skill.get("importance_score", 0.5),
                    "onet_code": skill.get("onet_code", ""),
                },
            )
            loaded += 1

        # Load prerequisite edges
        edges_created = 0
        for skill in skills:
            for prereq_id in skill.get("prerequisites", []):
                try:
                    await neo4j_manager.run_query(
                        CypherQueries.CREATE_PREREQUISITE,
                        {
                            "from_skill_id": prereq_id,
                            "to_skill_id": skill["skill_id"],
                            "strength": 1.0,
                        },
                    )
                    edges_created += 1
                except Exception as e:
                    logger.warning("graph.edge.failed", prereq=prereq_id, target=skill["skill_id"])

        logger.info("graph.seeded", skills=loaded, edges=edges_created)
        return loaded

    async def get_skill(self, skill_id: str) -> Optional[Dict]:
        results = await neo4j_manager.run_query(
            CypherQueries.GET_SKILL, {"skill_id": skill_id}
        )
        if not results:
            return None
        row = results[0]
        skill = dict(row["s"])
        skill["prerequisites"] = row.get("prerequisites", [])
        return skill

    async def get_prerequisites_recursive(
        self, skill_id: str, max_depth: int = 5
    ) -> List[Dict]:
        """Get all transitive prerequisites for a skill up to max_depth."""
        query = CypherQueries.GET_PREREQUISITES_RECURSIVE.replace(
            "{depth}", str(max_depth)
        ).replace("{skill_id}", "$skill_id")
        # Use f-string safe replacement for depth
        query = f"""
        MATCH path = (ancestor:Skill)-[:PREREQUISITE_OF*1..{max_depth}]->(target:Skill {{skill_id: $skill_id}})
        RETURN DISTINCT ancestor.skill_id as skill_id,
                       ancestor.name as name,
                       ancestor.domain as domain,
                       ancestor.difficulty_level as difficulty,
                       ancestor.avg_time_to_learn_hours as hours,
                       ancestor.importance_score as importance,
                       length(path) as depth
        ORDER BY depth ASC
        """
        return await neo4j_manager.run_query(query, {"skill_id": skill_id})

    async def get_subgraph_for_skills(
        self, skill_ids: List[str]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Return nodes and edges for a set of skill IDs.
        Used to build the frontend D3 graph.
        """
        if not skill_ids:
            return [], []

        results = await neo4j_manager.run_query(
            CypherQueries.GET_ALL_SKILLS_SUBGRAPH,
            {"skill_ids": skill_ids},
        )

        nodes = []
        edges = []
        seen_nodes: Set[str] = set()

        for row in results:
            skill = dict(row["s"])
            sid = skill.get("skill_id")
            if sid and sid not in seen_nodes:
                nodes.append(skill)
                seen_nodes.add(sid)
            for edge in row.get("edges", []):
                if edge.get("to"):
                    edges.append({"from": sid, "to": edge["to"], "strength": edge.get("strength", 1.0)})

        return nodes, edges

    async def build_networkx_graph(self, skill_ids: List[str]) -> nx.DiGraph:
        """
        Build a NetworkX DiGraph from Neo4j data for algorithmic processing.
        Used by the Path Engine for topological sort.
        """
        nodes, edges = await self.get_subgraph_for_skills(skill_ids)
        G = nx.DiGraph()

        for node in nodes:
            G.add_node(
                node["skill_id"],
                name=node.get("name", ""),
                domain=node.get("domain", ""),
                difficulty=node.get("difficulty_level", "intermediate"),
                hours=node.get("avg_time_to_learn_hours", 40),
                importance=node.get("importance_score", 0.5),
            )

        for edge in edges:
            G.add_edge(edge["from"], edge["to"], strength=edge.get("strength", 1.0))

        return G

    async def get_related_skills(
        self, skill_id: str, threshold: float = 0.7, limit: int = 10
    ) -> List[Dict]:
        return await neo4j_manager.run_query(
            CypherQueries.GET_RELATED_SKILLS,
            {"skill_id": skill_id, "threshold": threshold, "limit": limit},
        )

    async def skill_exists(self, skill_id: str) -> bool:
        results = await neo4j_manager.run_query(
            "MATCH (s:Skill {skill_id: $skill_id}) RETURN s.skill_id LIMIT 1",
            {"skill_id": skill_id},
        )
        return len(results) > 0

    async def get_graph_stats(self) -> Dict[str, int]:
        skill_count = await neo4j_manager.run_query(CypherQueries.SKILLS_COUNT)
        edge_count = await neo4j_manager.run_query(
            "MATCH ()-[r:PREREQUISITE_OF]->() RETURN count(r) as count"
        )
        return {
            "skill_count": skill_count[0]["count"] if skill_count else 0,
            "edge_count": edge_count[0]["count"] if edge_count else 0,
        }


_skill_graph_engine: Optional[SkillGraphEngine] = None


def get_skill_graph_engine() -> SkillGraphEngine:
    global _skill_graph_engine
    if _skill_graph_engine is None:
        _skill_graph_engine = SkillGraphEngine()
    return _skill_graph_engine
