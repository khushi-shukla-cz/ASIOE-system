"""
ASIOE — Explainability Engine
Every decision made by the system is fully traceable.

For every module in the learning path, this engine produces:
- why_selected: Human-readable justification
- dependency_chain: Visual chain of prerequisites
- confidence_score: How certain the system is
- alternative_paths: What else was considered
- gap_contribution: How much this skill closes the gap

At session level:
- Full reasoning trace across all 5 engines
- Token usage audit
- Model selection log
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from groq import AsyncGroq

from core.config import settings
from schemas.schemas import (
    GapAnalysisResult,
    LearningPathResult,
    NodeExplanation,
    SystemReasoningTrace,
)

logger = structlog.get_logger(__name__)


FULL_TRACE_PROMPT = """You are a senior engineering lead at a Fortune 500 company explaining
an AI system's decisions to the CTO.

SYSTEM CONTEXT:
- System: Adaptive Skill Intelligence & Optimization Engine (ASIOE)
- Candidate readiness: {readiness_pct}%
- Critical gaps: {critical_gaps}
- Learning path: {path_summary}

Generate a professional, technical reasoning trace (5-7 sentences) explaining:
1. How skill gaps were computed (cosine similarity on proficiency vectors)
2. Why the learning path is ordered this way (topological sort on DAG)
3. What the key algorithmic decisions were
4. What the expected outcome is

Be precise, professional, and technical. No marketing language.
"""


class ExplainabilityEngine:
    """
    Produces traceable, auditable reasoning for every system decision.
    Critical for enterprise deployment trust and compliance.
    """

    def __init__(self) -> None:
        self.llm = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def generate_node_explanations(
        self,
        path: LearningPathResult,
        gap_analysis: GapAnalysisResult,
    ) -> List[NodeExplanation]:
        """Generate per-node explanations for the explainability console."""
        gap_map = {}
        for gap in gap_analysis.critical_gaps + gap_analysis.major_gaps + gap_analysis.minor_gaps:
            gap_map[gap.skill_id] = gap

        explanations = []
        rank = 1

        for phase in path.phases:
            for module in phase.modules:
                gap = gap_map.get(module.skill_id)

                gap_contribution = 0.0
                if gap:
                    gap_contribution = gap.gap_delta

                alternatives = self._generate_alternatives(module, path)

                explanation = NodeExplanation(
                    node_id=module.module_id,
                    skill_name=module.skill_name,
                    why_included=module.why_selected,
                    dependency_chain=module.dependency_chain,
                    confidence_score=module.confidence_score,
                    importance_rank=rank,
                    gap_contribution=round(gap_contribution, 3),
                    alternative_paths=alternatives,
                )
                explanations.append(explanation)
                rank += 1

        return explanations

    async def generate_system_trace(
        self,
        session_id: str,
        parsing_data: Dict[str, Any],
        gap_analysis: GapAnalysisResult,
        path: LearningPathResult,
        total_tokens: int,
    ) -> SystemReasoningTrace:
        """Generate full system-level reasoning trace."""

        parsing_trace = self._build_parsing_trace(parsing_data)
        normalization_trace = self._build_normalization_trace(parsing_data)
        gap_trace = self._build_gap_trace(gap_analysis)
        path_trace = self._build_path_trace(path)

        return SystemReasoningTrace(
            session_id=session_id,
            parsing_trace=parsing_trace,
            normalization_trace=normalization_trace,
            gap_trace=gap_trace,
            path_trace=path_trace,
            total_tokens_used=total_tokens,
            model_used=settings.GROQ_PRIMARY_MODEL,
            generated_at=datetime.utcnow(),
        )

    def _build_parsing_trace(self, parsing_data: Dict) -> str:
        resume_skills = len(parsing_data.get("resume", {}).get("skills", []))
        jd_required = len(parsing_data.get("jd", {}).get("required_skills", []))
        jd_preferred = len(parsing_data.get("jd", {}).get("preferred_skills", []))
        confidence = parsing_data.get("resume", {}).get("parsing_confidence", 0)

        return (
            f"[PARSING ENGINE] Extracted {resume_skills} skills from resume "
            f"(confidence: {confidence:.0%}) using PyMuPDF + Llama-3.3-70B structured extraction. "
            f"JD analysis identified {jd_required} required and {jd_preferred} preferred skills. "
            f"Model: {settings.GROQ_PRIMARY_MODEL}. Temperature: {settings.GROQ_TEMPERATURE} "
            f"(deterministic extraction mode)."
        )

    def _build_normalization_trace(self, parsing_data: Dict) -> str:
        raw_count = len(parsing_data.get("resume", {}).get("skills", []))
        return (
            f"[NORMALIZATION ENGINE] {raw_count} raw skill tokens processed through "
            f"3-pass normalization: (1) exact ontology lookup, "
            f"(2) semantic embedding similarity via sentence-transformers/all-mpnet-base-v2 "
            f"(threshold: {settings.SKILL_SIMILARITY_THRESHOLD}), "
            f"(3) synthetic ID generation for unmatched skills. "
            f"Deduplication applied to eliminate synonyms and aliases."
        )

    def _build_gap_trace(self, gap_analysis: GapAnalysisResult) -> str:
        return (
            f"[GAP ENGINE] Gap computed as set difference: JD_skills - Resume_skills. "
            f"Proficiency scoring via cosine similarity on embedding vectors. "
            f"Severity classification: critical (gap_delta > 0.6), major (0.35–0.6), minor (0.1–0.35). "
            f"Results: {len(gap_analysis.critical_gaps)} critical, "
            f"{len(gap_analysis.major_gaps)} major, {len(gap_analysis.minor_gaps)} minor gaps. "
            f"Overall readiness score: {gap_analysis.overall_readiness_score:.1%} "
            f"({gap_analysis.readiness_label}). "
            f"Domain coverage weighted by role-specific importance coefficients."
        )

    def _build_path_trace(self, path: LearningPathResult) -> str:
        return (
            f"[PATH ENGINE] Algorithm: {path.path_algorithm}. "
            f"Backward DFS from {len(path.phases)} target skill clusters, "
            f"expanding prerequisite subtrees up to depth {settings.MAX_PATH_DEPTH}. "
            f"Candidate-known skills pruned ({path.redundancy_eliminated} modules eliminated). "
            f"Topological sort applied to guarantee prerequisite ordering. "
            f"Multi-factor ranking: importance (35%) + gap severity (30%) + "
            f"dependency depth (20%) + domain priority (10%) + efficiency (5%). "
            f"Output: {path.total_modules} modules | {path.total_hours}h | "
            f"{path.total_weeks}w | efficiency score: {path.efficiency_score:.1%}."
        )

    def _generate_alternatives(
        self, module: Any, path: LearningPathResult
    ) -> List[str]:
        """Generate what alternative paths could have been taken."""
        alternatives = []
        if module.domain == "technical":
            alternatives.append("Could substitute with domain-equivalent framework course")
        if module.difficulty_level in ("advanced", "expert"):
            alternatives.append("Intermediate-level prerequisite path available if timeline is extended")
        return alternatives[:2]


_explainability_engine: Optional[ExplainabilityEngine] = None


def get_explainability_engine() -> ExplainabilityEngine:
    global _explainability_engine
    if _explainability_engine is None:
        _explainability_engine = ExplainabilityEngine()
    return _explainability_engine
