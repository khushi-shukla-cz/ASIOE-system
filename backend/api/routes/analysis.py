"""
ASIOE — Analysis API Routes
Core endpoints for the adaptive onboarding engine.

POST /api/v1/analyze          — Upload resume + JD, run full pipeline
GET  /api/v1/sessions/{id}    — Get session status
GET  /api/v1/results/{id}     — Get complete analysis results
GET  /api/v1/explain/{id}     — Get per-node explanations
GET  /api/v1/graph/{id}       — Get skill graph data
GET  /api/v1/metrics/{id}     — Get session performance metrics
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.cache import build_cache_key, cache_get, cache_set
from db.database import get_db
from db.models import AnalysisSession, AuditLog, GapAnalysis, LearningPath, SkillProfile
from schemas.schemas import (
    AnalysisCompleteResponse,
    AnalyzeRequest,
    SessionResponse,
    SessionStatus,
)
from services.analysis_service import get_analysis_service

logger = structlog.get_logger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ── POST /analyze ──────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=AnalysisCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Full Adaptive Analysis",
    description=(
        "Upload a resume (PDF/DOCX/TXT) and provide a job description. "
        "The system will parse both documents, perform skill gap analysis, "
        "and generate a personalized adaptive learning path."
    ),
)
async def analyze(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    jd_text: str = Form(..., description="Job description text"),
    target_role: Optional[str] = Form(default=None),
    priority_mode: str = Form(default="balanced"),
    max_modules: int = Form(default=20),
    time_constraint_weeks: Optional[int] = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> AnalysisCompleteResponse:

    # Validate file type
    ext = (resume.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read and validate file size
    file_bytes = await resume.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )
    if len(file_bytes) < 100:
        raise HTTPException(status_code=422, detail="File appears to be empty or corrupted")

    # Build request object
    request = AnalyzeRequest(
        jd_text=jd_text,
        target_role=target_role,
        priority_mode=priority_mode,
        max_modules=max_modules,
        time_constraint_weeks=time_constraint_weeks,
    )

    # Create session
    service = get_analysis_service()
    session = await service.create_session(
        db=db,
        resume_filename=resume.filename or "resume",
        jd_text=jd_text,
        target_role=target_role,
    )

    # Run full pipeline
    result = await service.run_analysis(
        db=db,
        session_id=session.id,
        file_bytes=file_bytes,
        filename=resume.filename or "resume.pdf",
        request=request,
    )

    return result


# ── GET /sessions/{session_id} ────────────────────────────────────────────────

@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get Session Status",
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    result = await db.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionResponse(
        session_id=session.id,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        target_role=session.target_role,
    )


# ── GET /results/{session_id} ────────────────────────────────────────────────

@router.get(
    "/results/{session_id}",
    response_model=AnalysisCompleteResponse,
    summary="Get Complete Analysis Results",
)
async def get_results(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Check cache first
    cache_key = build_cache_key("analysis", session_id)
    cached = await cache_get(cache_key)
    if cached:
        return JSONResponse(content=cached)

    # Check session exists
    result = await db.execute(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if session.status == SessionStatus.PROCESSING:
        raise HTTPException(status_code=202, detail="Analysis still in progress")
    if session.status == SessionStatus.FAILED:
        raise HTTPException(status_code=500, detail="Analysis failed")

    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Analysis is not complete")

    profile_result = await db.execute(
        select(SkillProfile).where(SkillProfile.session_id == session_id)
    )
    profile = profile_result.scalar_one_or_none()

    gap_result = await db.execute(
        select(GapAnalysis).where(GapAnalysis.session_id == session_id)
    )
    gap = gap_result.scalar_one_or_none()

    path_result = await db.execute(
        select(LearningPath).where(LearningPath.session_id == session_id)
    )
    path = path_result.scalar_one_or_none()

    logs_result = await db.execute(
        select(AuditLog).where(AuditLog.session_id == session_id)
    )
    logs = logs_result.scalars().all()

    if not profile or not gap or not path:
        raise HTTPException(
            status_code=404,
            detail="Analysis artifacts are incomplete. Re-run analysis.",
        )

    reconstructed = _reconstruct_response(session, profile, gap, path, logs)
    await cache_set(cache_key, reconstructed.model_dump(mode="json"), ttl=settings.CACHE_TTL_SECONDS)
    return reconstructed


def _readiness_label(score: float) -> str:
    if score >= 0.8:
        return "Ready"
    if score >= 0.6:
        return "Near Ready"
    if score >= 0.4:
        return "Partial"
    return "Needs Work"


def _reconstruct_response(
    session: AnalysisSession,
    profile: SkillProfile,
    gap: GapAnalysis,
    path: LearningPath,
    logs: list[AuditLog],
) -> AnalysisCompleteResponse:
    extracted_skills = profile.extracted_skills or {}
    skills = list(extracted_skills.values()) if isinstance(extracted_skills, dict) else extracted_skills

    jd_required = profile.jd_required_skills or {}
    jd_required_skills = list(jd_required.values()) if isinstance(jd_required, dict) else jd_required

    now = datetime.now(timezone.utc)
    processing_time_ms = float(sum((log.duration_ms or 0) for log in logs))

    return AnalysisCompleteResponse(
        session_id=session.id,
        status=session.status,
        skill_profile={
            "candidate_name": profile.candidate_name,
            "current_role": profile.current_role,
            "years_of_experience": profile.years_of_experience,
            "education_level": profile.education_level,
            "skills": skills,
            "certifications": [],
            "parsing_confidence": profile.parsing_confidence,
            "target_role": session.target_role,
            "jd_required_skills": jd_required_skills,
        },
        gap_analysis={
            "session_id": session.id,
            "overall_readiness_score": gap.overall_readiness_score,
            "readiness_label": _readiness_label(gap.overall_readiness_score),
            "critical_gaps": gap.critical_gaps or [],
            "major_gaps": gap.major_gaps or [],
            "minor_gaps": gap.minor_gaps or [],
            "strength_areas": gap.strength_areas or [],
            "domain_coverage": gap.domain_coverage or [],
            "reasoning_trace": "Reconstructed from persisted analysis artifacts",
            "analysis_timestamp": gap.created_at or now,
        },
        learning_path={
            "session_id": session.id,
            "path_id": path.id,
            "target_role": session.target_role or "Target Role",
            "phases": path.phases or [],
            "total_modules": path.total_modules,
            "total_hours": path.estimated_hours,
            "total_weeks": path.estimated_weeks,
            "path_graph": path.path_graph or {"nodes": [], "edges": []},
            "efficiency_score": path.efficiency_score,
            "redundancy_eliminated": 0,
            "path_algorithm": path.path_algorithm,
            "path_version": path.path_version,
            "reasoning_trace": "Reconstructed from persisted analysis artifacts",
            "generated_at": path.created_at or now,
        },
        reasoning_trace=None,
        processing_time_ms=processing_time_ms,
    )


# ── GET /explain/{session_id} ─────────────────────────────────────────────────

@router.get(
    "/explain/{session_id}",
    summary="Get Per-Node Explainability Data",
)
async def get_explanations(session_id: str) -> Dict[str, Any]:
    cache_key = build_cache_key("analysis", session_id)
    cached = await cache_get(cache_key)
    if not cached:
        raise HTTPException(status_code=404, detail="Analysis results not found")

    # Extract explainability data from cached result
    learning_path = cached.get("learning_path", {})
    gap_analysis = cached.get("gap_analysis", {})
    trace = cached.get("reasoning_trace", {})

    modules_flat = []
    for phase in learning_path.get("phases", []):
        for module in phase.get("modules", []):
            modules_flat.append({
                "module_id": module.get("module_id"),
                "skill_name": module.get("skill_name"),
                "why_selected": module.get("why_selected"),
                "dependency_chain": module.get("dependency_chain", []),
                "confidence_score": module.get("confidence_score"),
                "importance_score": module.get("importance_score"),
                "phase": module.get("phase_number"),
                "domain": module.get("domain"),
                "estimated_hours": module.get("estimated_hours"),
            })

    return {
        "session_id": session_id,
        "module_explanations": modules_flat,
        "system_trace": trace,
        "gap_reasoning": gap_analysis.get("reasoning_trace", ""),
        "path_reasoning": learning_path.get("reasoning_trace", ""),
        "algorithm": learning_path.get("path_algorithm", ""),
        "efficiency_score": learning_path.get("efficiency_score", 0),
        "redundancy_eliminated": learning_path.get("redundancy_eliminated", 0),
    }


# ── GET /graph/{session_id} ───────────────────────────────────────────────────

@router.get(
    "/graph/{session_id}",
    summary="Get Skill Graph Visualization Data",
)
async def get_graph(session_id: str) -> Dict[str, Any]:
    cache_key = build_cache_key("analysis", session_id)
    cached = await cache_get(cache_key)
    if not cached:
        raise HTTPException(status_code=404, detail="Analysis results not found")

    path = cached.get("learning_path", {})
    gap = cached.get("gap_analysis", {})

    # Build enriched graph with gap severity annotations
    gap_map = {}
    for severity in ("critical_gaps", "major_gaps", "minor_gaps"):
        for g in gap.get(severity, []):
            gap_map[g.get("skill_id")] = severity.replace("_gaps", "")

    graph = path.get("path_graph", {"nodes": [], "edges": []})
    for node in graph.get("nodes", []):
        node["gap_severity"] = gap_map.get(node.get("skill_id"), "none")

    return {
        "session_id": session_id,
        "graph": graph,
        "domain_coverage": gap.get("domain_coverage", []),
        "readiness_score": gap.get("overall_readiness_score", 0),
    }


# ── GET /metrics/{session_id} ─────────────────────────────────────────────────

@router.get(
    "/metrics/{session_id}",
    summary="Get Session Performance Metrics",
)
async def get_metrics(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp)
    )
    logs = result.scalars().all()

    if not logs:
        raise HTTPException(status_code=404, detail="No metrics found for session")

    engine_timings = {}
    total_tokens = 0
    for log in logs:
        engine_timings[log.engine] = {
            "operation": log.operation,
            "duration_ms": log.duration_ms,
            "success": log.success,
        }
        total_tokens += (log.input_tokens or 0) + (log.output_tokens or 0)

    total_ms = sum(l.duration_ms or 0 for l in logs)

    return {
        "session_id": session_id,
        "engine_timings": engine_timings,
        "total_processing_ms": total_ms,
        "total_tokens_used": total_tokens,
        "all_engines_succeeded": all(l.success for l in logs),
    }
