"""
ASIOE — Neo4j Graph Database Manager
Manages the skill knowledge graph using Neo4j.
The DAG of skills and prerequisites lives here.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class Neo4jManager:
    """Singleton manager for Neo4j async driver."""

    _driver: Optional[AsyncDriver] = None

    @classmethod
    async def connect(cls) -> None:
        if cls._driver is not None:
            return
        cls._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=50,
            connection_acquisition_timeout=30,
        )
        await cls._driver.verify_connectivity()
        logger.info("neo4j.connected", uri=settings.NEO4J_URI)

    @classmethod
    async def close(cls) -> None:
        if cls._driver:
            await cls._driver.close()
            cls._driver = None
            logger.info("neo4j.closed")

    @classmethod
    @asynccontextmanager
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        if cls._driver is None:
            await cls.connect()
        async with cls._driver.session() as session:
            yield session

    @classmethod
    async def run_query(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return all results as dicts."""
        async with cls.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    @classmethod
    async def create_constraints(cls) -> None:
        """Create uniqueness constraints and indexes for production performance."""
        constraints = [
            "CREATE CONSTRAINT skill_id_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE",
            "CREATE CONSTRAINT domain_id_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.domain_id IS UNIQUE",
            "CREATE CONSTRAINT role_id_unique IF NOT EXISTS FOR (r:Role) REQUIRE r.role_id IS UNIQUE",
            "CREATE CONSTRAINT course_id_unique IF NOT EXISTS FOR (c:Course) REQUIRE c.course_id IS UNIQUE",
            "CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name)",
            "CREATE INDEX skill_domain_idx IF NOT EXISTS FOR (s:Skill) ON (s.domain)",
            "CREATE INDEX skill_difficulty_idx IF NOT EXISTS FOR (s:Skill) ON (s.difficulty_level)",
        ]
        async with cls.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    logger.warning("neo4j.constraint.skip", query=constraint, reason=str(e))
        logger.info("neo4j.constraints.created")


neo4j_manager = Neo4jManager()
