"""
ASIOE — Analysis Service
Orchestrates the complete analysis pipeline:
Upload → Parse → Normalize → Graph → Gap → Path → RAG → Explain → Persist

This is the main service layer called by the API routes.
Handles session management, error recovery, and audit logging.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from db.cache import build_cache_key, cache_get, cache_set
from db.models import AnalysisSession, AuditLog, GapAnalysis, LearningPath, SkillProfile
from schemas.schemas import (
    AnalysisCompleteResponse,
    AnalyzeRequest,
    SessionResponse,
    SessionStatus,
)
from services.analysis_workflow import AnalysisPipelineInput, get_analysis_workflow

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
        # Check cache first
        cache_key = build_cache_key("analysis", session_id)
        cached = await cache_get(cache_key)
        if cached:
            logger.info("analysis.cache_hit", session_id=session_id)
            return AnalysisCompleteResponse(**cached)

        await self._update_session_status(db, session_id, SessionStatus.PROCESSING)

        try:
            workflow = get_analysis_workflow()
            analysis_input = AnalysisPipelineInput.from_request(request)
            pipeline_result = await workflow.execute(
                session_id=session_id,
                file_bytes=file_bytes,
                filename=filename,
                analysis_input=analysis_input,
            )

            await self._log_audit(
                db,
                session_id,
                "analysis_workflow",
                "pipeline_execute",
                int(pipeline_result.processing_time_ms),
                True,
            )

            # ── Persist to PostgreSQL ─────────────────────────────────────────
            await self._persist_results(
                db, session_id, pipeline_result
            )

            await self._update_session_status(db, session_id, SessionStatus.COMPLETED)

            response = AnalysisCompleteResponse(
                session_id=session_id,
                status=SessionStatus.COMPLETED,
                skill_profile=pipeline_result.skill_profile,
                gap_analysis=pipeline_result.gap_result,
                learning_path=pipeline_result.path_result,
                reasoning_trace=pipeline_result.reasoning_trace,
                processing_time_ms=pipeline_result.processing_time_ms,
            )

            # Cache result (60 min TTL)
            await cache_set(cache_key, response.model_dump(), ttl=3600)

            logger.info(
                "analysis.complete",
                session_id=session_id,
                total_ms=round(pipeline_result.processing_time_ms),
                modules=pipeline_result.path_result.total_modules,
                readiness=pipeline_result.gap_result.overall_readiness_score,
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
        pipeline_result: "AnalysisPipelineResult",
    ) -> None:
        resume_data = pipeline_result.resume_data
        gap_result = pipeline_result.gap_result
        path_result = pipeline_result.path_result

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
