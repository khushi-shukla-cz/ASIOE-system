"""
ASIOE — Simulation Routes
Allows users to adjust constraints and get a recomputed learning path
without re-running the full pipeline.

POST /api/v1/simulate — Recompute path with new constraints
"""
from __future__ import annotations

from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, HTTPException
from db.cache import build_cache_key, cache_get, cache_set
from core.resilience import run_with_resilience
from engines.path.path_engine import get_path_engine
from engines.rag.rag_engine import get_rag_engine
from schemas.schemas import GapAnalysisResult, SimulationRequest

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/simulate",
    summary="Simulate Learning Path with New Constraints",
    description=(
        "Recompute the learning path using updated time constraints or domain priorities "
        "without re-running the full parsing and gap analysis pipeline."
    ),
)
async def simulate(request: SimulationRequest) -> Dict[str, Any]:
    # Load cached analysis results
    cache_key = build_cache_key("analysis", request.session_id)
    cached = await cache_get(cache_key)
    if not cached:
        raise HTTPException(
            status_code=404,
            detail="Analysis results not found. Please run /analyze first.",
        )

    # Reconstruct gap analysis from cached data
    gap_data = cached.get("gap_analysis", {})
    if not gap_data:
        raise HTTPException(status_code=400, detail="Gap analysis data unavailable")

    gap_result = GapAnalysisResult(**gap_data)

    # Get candidate skill IDs from cached skill profile
    profile = cached.get("skill_profile", {})
    candidate_skill_ids = {
        s.get("canonical_skill_id", s.get("name", ""))
        for s in profile.get("skills", [])
    } - {""}

    # Recompute path with new constraints
    path_engine = get_path_engine()
    requested_max_modules = request.max_modules or 20
    new_path = await run_with_resilience(
        operation_name="simulation.path.generate",
        func=lambda: path_engine.generate_path(
            session_id=request.session_id,
            gap_analysis=gap_result,
            candidate_skill_ids=candidate_skill_ids,
            max_modules=requested_max_modules,
            time_constraint_weeks=request.time_constraint_weeks,
            priority_domains=request.priority_domains,
        ),
    )

    # Re-enrich with courses
    rag_engine = get_rag_engine()
    all_modules = [m for phase in new_path.phases for m in phase.modules]
    enriched = await run_with_resilience(
        operation_name="simulation.rag.enrich",
        func=lambda: rag_engine.enrich_modules(all_modules),
    )
    module_map = {m.module_id: m for m in enriched}
    for phase in new_path.phases:
        phase.modules = [module_map.get(m.module_id, m) for m in phase.modules]

    # Exclude specific modules if requested
    if request.exclude_module_ids:
        for phase in new_path.phases:
            phase.modules = [
                m for m in phase.modules
                if m.module_id not in request.exclude_module_ids
            ]

    # Cache the simulation result under a different key
    sim_key = build_cache_key("simulation", request.session_id, str(request.time_constraint_weeks))
    await cache_set(sim_key, new_path.model_dump(), ttl=1800)

    original_phases: List[Dict[str, Any]] = cached.get("learning_path", {}).get("phases", [])
    original_module_count = sum(len(phase.get("modules", [])) for phase in original_phases)
    original_hours = cached.get("learning_path", {}).get("total_hours", 0)
    simulated_hours = new_path.total_hours

    return {
        "session_id": request.session_id,
        "simulation_key": sim_key,
        "simulation_applied": True,
        "time_constraint_weeks": request.time_constraint_weeks,
        "max_modules": requested_max_modules,
        "priority_domains": request.priority_domains,
        "learning_path": new_path.model_dump(),
        "delta": {
            "original_modules": original_module_count,
            "simulated_modules": new_path.total_modules,
            "module_delta": new_path.total_modules - original_module_count,
            "original_hours": original_hours,
            "simulated_hours": simulated_hours,
            "hour_delta": simulated_hours - original_hours,
        },
    }
