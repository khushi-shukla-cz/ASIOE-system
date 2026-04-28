"""
ASIOE — Analysis Workflow
Owns the domain pipeline for a single analysis execution:
Parse → Gap → Path → RAG → Explainability

This layer is intentionally side-effect free with respect to persistence and caching.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional, Set

from core.resilience import run_with_resilience
from engines.explainability.explainability_engine import get_explainability_engine
from engines.gap.gap_engine import get_gap_engine
from engines.parsing.parsing_engine import get_parsing_engine
from engines.path.path_engine import get_path_engine
from engines.rag.rag_engine import get_rag_engine
from schemas.schemas import AnalyzeRequest


@dataclass(frozen=True, slots=True)
class AnalysisPipelineInput:
    """Immutable input for a single analysis run."""

    jd_text: str
    target_role: Optional[str]
    priority_mode: str
    max_modules: int
    time_constraint_weeks: Optional[int]

    @classmethod
    def from_request(cls, request: AnalyzeRequest) -> "AnalysisPipelineInput":
        return cls(
            jd_text=request.jd_text,
            target_role=request.target_role,
            priority_mode=request.priority_mode,
            max_modules=request.max_modules,
            time_constraint_weeks=request.time_constraint_weeks,
        )


@dataclass(slots=True)
class AnalysisPipelineResult:
    """Explicit output of the analysis workflow."""

    session_id: str
    resume_data: dict[str, Any]
    jd_data: dict[str, Any]
    gap_result: Any
    path_result: Any
    reasoning_trace: Any
    target_role: str
    total_tokens: int
    processing_time_ms: float

    @property
    def candidate_skill_ids(self) -> Set[str]:
        return {
            skill.get("canonical_skill_id", "")
            for skill in self.resume_data.get("skills", [])
        } - {""}

    @property
    def skill_profile(self) -> dict[str, Any]:
        return {
            "candidate_name": self.resume_data.get("candidate_name"),
            "current_role": self.resume_data.get("current_role"),
            "years_of_experience": self.resume_data.get("years_of_experience"),
            "education_level": self.resume_data.get("education_level"),
            "skills": self.resume_data.get("skills", [])[:30],
            "certifications": self.resume_data.get("certifications", []),
            "parsing_confidence": self.resume_data.get("parsing_confidence", 0),
            "target_role": self.target_role,
            "jd_required_skills": self.jd_data.get("required_skills", []),
        }


class AnalysisWorkflow:
    """Encapsulates the core analysis pipeline steps."""

    async def execute(
        self,
        session_id: str,
        file_bytes: bytes,
        filename: str,
        analysis_input: AnalysisPipelineInput,
    ) -> AnalysisPipelineResult:
        pipeline_start = time.perf_counter()
        total_tokens = 0

        parsing_engine = get_parsing_engine()
        resume_data = await run_with_resilience(
            operation_name="parsing.parse_resume",
            func=lambda: parsing_engine.parse_resume(file_bytes, filename),
        )
        jd_data = await run_with_resilience(
            operation_name="parsing.parse_jd",
            func=lambda: parsing_engine.parse_jd(analysis_input.jd_text),
        )
        total_tokens += resume_data.get("input_tokens", 0) + resume_data.get("output_tokens", 0)
        total_tokens += jd_data.get("input_tokens", 0) + jd_data.get("output_tokens", 0)

        effective_target_role = analysis_input.target_role or jd_data.get("target_role", "Target Role")

        gap_engine = get_gap_engine()
        gap_result = await run_with_resilience(
            operation_name="gap.analyze",
            func=lambda: gap_engine.analyze(session_id, resume_data, jd_data),
        )

        path_engine = get_path_engine()
        path_result = await run_with_resilience(
            operation_name="path.generate",
            func=lambda: path_engine.generate_path(
                session_id=session_id,
                gap_analysis=gap_result,
                candidate_skill_ids={
                    skill.get("canonical_skill_id", "")
                    for skill in resume_data.get("skills", [])
                } - {""},
                max_modules=analysis_input.max_modules,
                time_constraint_weeks=analysis_input.time_constraint_weeks,
            ),
        )
        path_result = path_result.model_copy(update={"target_role": effective_target_role})

        rag_engine = get_rag_engine()
        all_modules = [module for phase in path_result.phases for module in phase.modules]
        enriched_modules = await run_with_resilience(
            operation_name="rag.enrich_modules",
            func=lambda: rag_engine.enrich_modules(all_modules),
        )

        module_map = {module.module_id: module for module in enriched_modules}
        path_result = path_result.model_copy(
            update={
                "phases": [
                    phase.model_copy(
                        update={
                            "modules": [
                                module_map.get(module.module_id, module)
                                for module in phase.modules
                            ]
                        }
                    )
                    for phase in path_result.phases
                ]
            }
        )

        explain_engine = get_explainability_engine()
        trace = await run_with_resilience(
            operation_name="explainability.generate_trace",
            func=lambda: explain_engine.generate_system_trace(
                session_id=session_id,
                parsing_data={"resume": resume_data, "jd": jd_data},
                gap_analysis=gap_result,
                path=path_result,
                total_tokens=total_tokens,
            ),
        )

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        return AnalysisPipelineResult(
            session_id=session_id,
            resume_data=resume_data,
            jd_data=jd_data,
            gap_result=gap_result,
            path_result=path_result,
            reasoning_trace=trace,
            target_role=effective_target_role,
            total_tokens=total_tokens,
            processing_time_ms=round(total_ms, 2),
        )


def get_analysis_workflow() -> AnalysisWorkflow:
    return AnalysisWorkflow()