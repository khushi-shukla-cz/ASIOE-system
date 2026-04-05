"""
ASIOE — Analysis Service
Orchestrates the complete analysis pipeline:
Upload → Parse → Normalize → Graph → Gap → Path → RAG → Explain → Persist

This is the main service layer called by the API routes.
Handles session management, error recovery, and audit logging.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Set

import structlog
from core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from db.cache import build_cache_key, cache_get, cache_set
from db.models import AnalysisSession, AuditLog, GapAnalysis, LearningPath, SkillProfile
from engines.explainability.explainability_engine import get_explainability_engine
from engines.gap.gap_engine import get_gap_engine
from engines.parsing.parsing_engine import get_parsing_engine
from engines.path.path_engine import get_path_engine
from engines.rag.rag_engine import get_rag_engine
from schemas.schemas import (
    AnalysisCompleteResponse,
    AnalyzeRequest,
    SessionResponse,
    SessionStatus,
)

logger = structlog.get_logger(__name__)


class AnalysisService:
    """Main orchestration service for the ASIOE analysis pipeline."""

    async def create_session(
        self,
        db: AsyncSession,
        resume_filename: str,
        jd_text: str,
        target_role: Optional[str] = None,
    ) -> AnalysisSession:
        """Create a new analysis session record."""
        import hashlib
        session = AnalysisSession(
            id=str(uuid.uuid4()),
            status=SessionStatus.PENDING,
            resume_filename=resume_filename,
            jd_text_hash=hashlib.md5(jd_text.encode()).hexdigest(),
            target_role=target_role,
        )
        db.add(session)
        await db.flush()
        logger.info("session.created", session_id=session.id)
        return session

    async def run_analysis(
        self,
        db: AsyncSession,
        session_id: str,
        file_bytes: bytes,
        filename: str,
        request: AnalyzeRequest,
    ) -> AnalysisCompleteResponse:
        """
        Execute the full analysis pipeline end-to-end.
        Updates session status throughout and persists all results.
        """
        pipeline_start = time.perf_counter()
        total_tokens = 0

        # Check cache first
        cache_key = build_cache_key("analysis", session_id)
        cached = await cache_get(cache_key)
        if cached:
            logger.info("analysis.cache_hit", session_id=session_id)
            return AnalysisCompleteResponse(**cached)

        await self._update_session_status(db, session_id, SessionStatus.PROCESSING)

        try:
            # ── Engine 1: Parse Resume ────────────────────────────────────────
            t0 = time.perf_counter()
            parsing_engine = get_parsing_engine()
            resume_data = await parsing_engine.parse_resume(file_bytes, filename)
            jd_data = await parsing_engine.parse_jd(request.jd_text)
            total_tokens += resume_data.get("input_tokens", 0) + resume_data.get("output_tokens", 0)
            total_tokens += jd_data.get("input_tokens", 0) + jd_data.get("output_tokens", 0)
            await self._log_audit(db, session_id, "parsing_engine", "parse_resume_jd",
                                  int((time.perf_counter()-t0)*1000), True)

            # Enrich with target role from JD if not provided
            if not request.target_role:
                request.target_role = jd_data.get("target_role", "Target Role")

            # ── Engine 2: Gap Analysis ────────────────────────────────────────
            t0 = time.perf_counter()
            gap_engine = get_gap_engine()
            gap_result = await gap_engine.analyze(session_id, resume_data, jd_data)
            await self._log_audit(db, session_id, "gap_engine", "gap_analysis",
                                  int((time.perf_counter()-t0)*1000), True)

            # ── Engine 3: Adaptive Path ───────────────────────────────────────
            t0 = time.perf_counter()
            path_engine = get_path_engine()
            candidate_skill_ids: Set[str] = {
                s.get("canonical_skill_id", "")
                for s in resume_data.get("skills", [])
            } - {""}

            path_result = await path_engine.generate_path(
                session_id=session_id,
                gap_analysis=gap_result,
                candidate_skill_ids=candidate_skill_ids,
                max_modules=request.max_modules,
                time_constraint_weeks=request.time_constraint_weeks,
            )
            # Set target role on path
            path_result.target_role = request.target_role or "Target Role"
            await self._log_audit(db, session_id, "path_engine", "generate_path",
                                  int((time.perf_counter()-t0)*1000), True)

            # ── Engine 4: RAG Course Enrichment ──────────────────────────────
            t0 = time.perf_counter()
            rag_engine = get_rag_engine()
            all_modules = [m for phase in path_result.phases for m in phase.modules]
            enriched_modules = await rag_engine.enrich_modules(all_modules)

            # Re-assign enriched modules back to phases
            module_map = {m.module_id: m for m in enriched_modules}
            for phase in path_result.phases:
                phase.modules = [module_map.get(m.module_id, m) for m in phase.modules]

            await self._log_audit(db, session_id, "rag_engine", "enrich_modules",
                                  int((time.perf_counter()-t0)*1000), True)

            # ── Engine 5: Explainability ──────────────────────────────────────
            t0 = time.perf_counter()
            explain_engine = get_explainability_engine()
            trace = await explain_engine.generate_system_trace(
                session_id=session_id,
                parsing_data={"resume": resume_data, "jd": jd_data},
                gap_analysis=gap_result,
                path=path_result,
                total_tokens=total_tokens,
            )
            await self._log_audit(db, session_id, "explainability_engine", "system_trace",
                                  int((time.perf_counter()-t0)*1000), True)

            # ── Persist to PostgreSQL ─────────────────────────────────────────
            await self._persist_results(
                db, session_id, resume_data, gap_result, path_result
            )

            await self._update_session_status(db, session_id, SessionStatus.COMPLETED)

            total_ms = (time.perf_counter() - pipeline_start) * 1000

            response = AnalysisCompleteResponse(
                session_id=session_id,
                status=SessionStatus.COMPLETED,
                skill_profile={
                    "candidate_name": resume_data.get("candidate_name"),
                    "current_role": resume_data.get("current_role"),
                    "years_of_experience": resume_data.get("years_of_experience"),
                    "education_level": resume_data.get("education_level"),
                    "skills": resume_data.get("skills", [])[:30],
                    "certifications": resume_data.get("certifications", []),
                    "parsing_confidence": resume_data.get("parsing_confidence", 0),
                    "target_role": request.target_role,
                    "jd_required_skills": jd_data.get("required_skills", []),
                },
                gap_analysis=gap_result,
                learning_path=path_result,
                reasoning_trace=trace,
                processing_time_ms=round(total_ms, 2),
            )

            # Cache result (60 min TTL)
            await cache_set(cache_key, response.model_dump(), ttl=3600)

            logger.info(
                "analysis.complete",
                session_id=session_id,
                total_ms=round(total_ms),
                modules=path_result.total_modules,
                readiness=gap_result.overall_readiness_score,
            )
            return response

        except Exception as exc:
            await self._update_session_status(db, session_id, SessionStatus.FAILED)
            await self._log_audit(db, session_id, "analysis_service", "run_analysis",
                                  0, False, str(exc))
            logger.error("analysis.failed", session_id=session_id, error=str(exc), exc_info=True)
            raise

    async def _update_session_status(
        self, db: AsyncSession, session_id: str, status: SessionStatus
    ) -> None:
        from sqlalchemy import update
        await db.execute(
            update(AnalysisSession)
            .where(AnalysisSession.id == session_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await db.flush()

    async def _persist_results(
        self,
        db: AsyncSession,
        session_id: str,
        resume_data: Dict,
        gap_result: Any,
        path_result: Any,
    ) -> None:
        # Skill Profile
        profile = SkillProfile(
            session_id=session_id,
            candidate_name=resume_data.get("candidate_name"),
            candidate_email=resume_data.get("candidate_email"),
            years_of_experience=resume_data.get("years_of_experience"),
            education_level=resume_data.get("education_level"),
            current_role=resume_data.get("current_role"),
            extracted_skills={s.get("name", ""): s for s in resume_data.get("skills", [])},
            parsing_confidence=resume_data.get("parsing_confidence", 0),
            extraction_model=settings.GROQ_PRIMARY_MODEL,
        )
        db.add(profile)

        # Gap Analysis
        gap_record = GapAnalysis(
            session_id=session_id,
            overall_readiness_score=gap_result.overall_readiness_score,
            critical_gaps=[g.model_dump() for g in gap_result.critical_gaps],
            major_gaps=[g.model_dump() for g in gap_result.major_gaps],
            minor_gaps=[g.model_dump() for g in gap_result.minor_gaps],
            strength_areas=gap_result.strength_areas,
            domain_coverage=[d.model_dump() for d in gap_result.domain_coverage],
        )
        db.add(gap_record)

        # Learning Path
        path_record = LearningPath(
            session_id=session_id,
            total_modules=path_result.total_modules,
            estimated_hours=path_result.total_hours,
            estimated_weeks=path_result.total_weeks,
            phases=[p.model_dump() for p in path_result.phases],
            path_graph=path_result.path_graph,
            efficiency_score=path_result.efficiency_score,
            path_algorithm=path_result.path_algorithm,
            path_version=path_result.path_version,
        )
        db.add(path_record)
        await db.flush()

    async def _log_audit(
        self,
        db: AsyncSession,
        session_id: str,
        engine: str,
        operation: str,
        duration_ms: int,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            session_id=session_id,
            engine=engine,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error_message=error,
        )
        db.add(log)
        await db.flush()


def get_analysis_service() -> AnalysisService:
    return AnalysisService()
