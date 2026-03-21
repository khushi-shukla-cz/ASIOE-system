"""
ASIOE — Gap Analysis Engine
Computes the precise skill gap between a candidate profile and role requirements.

Algorithm:
1. Normalize both skill sets to canonical IDs
2. Set difference: JD_skills - Resume_skills = raw_gaps
3. Weighted cosine similarity for partial matches
4. Domain-level coverage scoring (for radar chart)
5. Readiness score = weighted coverage across domains
6. Classify gaps: critical | major | minor
7. Generate LLM reasoning trace
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from groq import AsyncGroq
from sklearn.metrics.pairwise import cosine_similarity

from core.config import settings
from engines.normalization.normalization_engine import get_normalization_engine
from schemas.schemas import DomainCoverage, GapAnalysisResult, GapSeverity, SkillGap, SkillDomain

logger = structlog.get_logger(__name__)


GAP_REASONING_PROMPT = """You are a senior talent development strategist.
Analyze this skill gap profile and provide a concise, professional reasoning trace.

CANDIDATE PROFILE:
- Current skills: {candidate_skills}
- Years of experience: {years_exp}
- Current role: {current_role}

TARGET ROLE: {target_role}
CRITICAL GAPS: {critical_gaps}
MAJOR GAPS: {major_gaps}
OVERALL READINESS: {readiness_pct}%

Provide a 3-4 sentence professional assessment covering:
1. The candidate's strongest transferable assets
2. The most critical development areas
3. Realistic timeline to role readiness

Be specific, data-driven, and constructive. No fluff.
"""

# Domain weights for readiness calculation (role-type agnostic baseline)
DOMAIN_WEIGHTS: Dict[str, float] = {
    "technical": 0.35,
    "analytical": 0.25,
    "domain_specific": 0.15,
    "leadership": 0.10,
    "communication": 0.08,
    "operational": 0.05,
    "soft_skills": 0.02,
}

GAP_SEVERITY_THRESHOLDS = {
    GapSeverity.CRITICAL: 0.6,   # gap_delta > 0.6 → critical
    GapSeverity.MAJOR: 0.35,     # gap_delta 0.35–0.6 → major
    GapSeverity.MINOR: 0.1,      # gap_delta 0.1–0.35 → minor
}


class GapAnalysisEngine:
    """
    Computes skill gaps between a normalized candidate profile
    and normalized JD requirements.
    """

    def __init__(self) -> None:
        self.normalizer = get_normalization_engine()
        self.llm = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def analyze(
        self,
        session_id: str,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
    ) -> GapAnalysisResult:
        start = time.perf_counter()

        # Step 1: Build candidate skill map {skill_id → skill_dict}
        candidate_map = self._build_skill_map(resume_data.get("skills", []))

        # Step 2: Build JD skill map {skill_id → skill_dict}
        all_jd_skills = (
            jd_data.get("required_skills", []) + jd_data.get("preferred_skills", [])
        )
        # Tag required vs preferred
        for s in jd_data.get("required_skills", []):
            s["_required"] = True
        for s in jd_data.get("preferred_skills", []):
            s["_required"] = False

        jd_map = self._build_skill_map(all_jd_skills)

        # Step 3: Compute gaps using cosine similarity on proficiency vectors
        gaps = self._compute_gaps(candidate_map, jd_map)

        # Step 4: Classify gaps
        critical, major, minor = self._classify_gaps(gaps)

        # Step 5: Identify strengths (skills candidate has that JD values)
        strengths = self._identify_strengths(candidate_map, jd_map)

        # Step 6: Domain coverage analysis
        domain_coverage = self._compute_domain_coverage(candidate_map, jd_map)

        # Step 7: Overall readiness score
        readiness_score = self._compute_readiness_score(domain_coverage, critical, major)

        # Step 8: Generate LLM reasoning trace
        reasoning = await self._generate_reasoning_trace(
            resume_data=resume_data,
            jd_data=jd_data,
            critical_gaps=critical,
            major_gaps=major,
            readiness_score=readiness_score,
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "gap.analysis.complete",
            session=session_id,
            readiness=round(readiness_score, 3),
            critical=len(critical),
            major=len(major),
            ms=int(elapsed * 1000),
        )

        return GapAnalysisResult(
            session_id=session_id,
            overall_readiness_score=round(readiness_score, 4),
            readiness_label=self._readiness_label(readiness_score),
            critical_gaps=critical,
            major_gaps=major,
            minor_gaps=minor,
            strength_areas=strengths,
            domain_coverage=domain_coverage,
            reasoning_trace=reasoning,
            analysis_timestamp=__import__("datetime").datetime.utcnow(),
        )

    def _build_skill_map(self, skills: List[Dict]) -> Dict[str, Dict]:
        """Build {canonical_skill_id → skill_dict} from a list of extracted skills."""
        normalized = self.normalizer.normalize_skill_list(skills)
        result = {}
        for skill in normalized:
            sid = skill.get("canonical_skill_id")
            if sid:
                result[sid] = skill
        return result

    def _compute_gaps(
        self,
        candidate: Dict[str, Dict],
        jd: Dict[str, Dict],
    ) -> List[Dict]:
        """
        For each required JD skill, compute:
        - current_score (candidate's level or 0)
        - required_score (JD requirement)
        - gap_delta
        """
        gaps = []
        for skill_id, jd_skill in jd.items():
            required_score = jd_skill.get("proficiency_score", 0.7)
            candidate_skill = candidate.get(skill_id)

            if candidate_skill:
                current_score = candidate_skill.get("proficiency_score", 0.0)
            else:
                # Semantic partial match: check if candidate has a similar skill
                current_score = self._find_partial_match(skill_id, jd_skill, candidate)

            gap_delta = max(0.0, required_score - current_score)

            if gap_delta >= 0.05:  # Only include meaningful gaps
                gaps.append({
                    "skill_id": skill_id,
                    "skill_name": jd_skill.get("name", skill_id),
                    "domain": jd_skill.get("domain", "technical"),
                    "current_score": round(current_score, 3),
                    "required_score": round(required_score, 3),
                    "gap_delta": round(gap_delta, 3),
                    "is_required": jd_skill.get("_required", True),
                })

        return sorted(gaps, key=lambda x: x["gap_delta"], reverse=True)

    def _find_partial_match(
        self,
        target_skill_id: str,
        target_skill: Dict,
        candidate: Dict[str, Dict],
    ) -> float:
        """
        Use semantic similarity to find if candidate has a related skill.
        Returns effective proficiency score (0 if no match).
        """
        if not candidate:
            return 0.0

        target_name = target_skill.get("name", target_skill_id)
        candidate_names = [v.get("name", k) for k, v in candidate.items()]

        if not candidate_names:
            return 0.0

        model = self.normalizer._load_model()
        target_emb = model.encode([target_name], normalize_embeddings=True)
        cand_embs = model.encode(candidate_names, normalize_embeddings=True)

        sims = cosine_similarity(target_emb, cand_embs)[0]
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        if best_sim >= 0.75:
            # Partial credit proportional to similarity
            cand_values = list(candidate.values())
            cand_score = cand_values[best_idx].get("proficiency_score", 0.3)
            return round(cand_score * best_sim, 3)

        return 0.0

    def _classify_gaps(
        self, gaps: List[Dict]
    ) -> Tuple[List[SkillGap], List[SkillGap], List[SkillGap]]:
        critical, major, minor = [], [], []

        for gap in gaps:
            delta = gap["gap_delta"]

            if delta >= GAP_SEVERITY_THRESHOLDS[GapSeverity.CRITICAL]:
                severity = GapSeverity.CRITICAL
                target = critical
            elif delta >= GAP_SEVERITY_THRESHOLDS[GapSeverity.MAJOR]:
                severity = GapSeverity.MAJOR
                target = major
            else:
                severity = GapSeverity.MINOR
                target = minor

            skill_gap = SkillGap(
                skill_id=gap["skill_id"],
                skill_name=gap["skill_name"],
                domain=gap["domain"],
                severity=severity,
                current_score=gap["current_score"],
                required_score=gap["required_score"],
                gap_delta=gap["gap_delta"],
                reasoning=self._gap_reasoning(gap, severity),
            )
            target.append(skill_gap)

        return critical, major, minor

    def _gap_reasoning(self, gap: Dict, severity: GapSeverity) -> str:
        delta_pct = int(gap["gap_delta"] * 100)
        if severity == GapSeverity.CRITICAL:
            return (
                f"Candidate has {int(gap['current_score']*100)}% proficiency; "
                f"role requires {int(gap['required_score']*100)}%. "
                f"A {delta_pct}% gap in {gap['skill_name']} represents a blocking deficiency."
            )
        elif severity == GapSeverity.MAJOR:
            return (
                f"Partial proficiency detected ({int(gap['current_score']*100)}%). "
                f"Structured upskilling needed to reach {int(gap['required_score']*100)}% requirement."
            )
        else:
            return (
                f"Minor gap ({delta_pct}%). "
                f"Candidate is near-competent; targeted refinement advised."
            )

    def _identify_strengths(
        self,
        candidate: Dict[str, Dict],
        jd: Dict[str, Dict],
    ) -> List[Dict]:
        """Skills candidate has that exceed JD requirements."""
        strengths = []
        for skill_id, cand_skill in candidate.items():
            jd_skill = jd.get(skill_id)
            if jd_skill:
                req = jd_skill.get("proficiency_score", 0.5)
                curr = cand_skill.get("proficiency_score", 0.0)
                if curr >= req:
                    strengths.append({
                        **cand_skill,
                        "exceeds_by": round(curr - req, 3),
                    })
        return sorted(strengths, key=lambda x: x.get("proficiency_score", 0), reverse=True)[:10]

    def _compute_domain_coverage(
        self,
        candidate: Dict[str, Dict],
        jd: Dict[str, Dict],
    ) -> List[DomainCoverage]:
        """Compute coverage percentage per domain."""
        domain_data: Dict[str, Dict] = {}

        for skill_id, jd_skill in jd.items():
            domain = jd_skill.get("domain", "technical")
            if domain not in domain_data:
                domain_data[domain] = {"total": 0, "matched": 0, "score_sum": 0.0}
            domain_data[domain]["total"] += 1

            cand_skill = candidate.get(skill_id)
            req_score = jd_skill.get("proficiency_score", 0.7)
            curr_score = cand_skill.get("proficiency_score", 0.0) if cand_skill else 0.0

            if curr_score >= req_score * 0.8:  # 80% threshold for "matched"
                domain_data[domain]["matched"] += 1
            domain_data[domain]["score_sum"] += min(curr_score / max(req_score, 0.01), 1.0)

        coverages = []
        for domain, data in domain_data.items():
            total = data["total"]
            matched = data["matched"]
            coverage_pct = (matched / total * 100) if total > 0 else 0.0
            radar_value = (data["score_sum"] / total) if total > 0 else 0.0

            coverages.append(DomainCoverage(
                domain=domain,
                coverage_percentage=round(coverage_pct, 1),
                matched_skills=matched,
                total_required=total,
                radar_value=round(radar_value, 3),
            ))

        return sorted(coverages, key=lambda x: x.coverage_percentage, reverse=True)

    def _compute_readiness_score(
        self,
        domain_coverage: List[DomainCoverage],
        critical_gaps: List[SkillGap],
        major_gaps: List[SkillGap],
    ) -> float:
        """
        Weighted readiness score:
        - Domain coverage weighted by domain importance
        - Penalized for critical and major gaps
        """
        if not domain_coverage:
            return 0.0

        weighted_sum = 0.0
        weight_sum = 0.0
        for dc in domain_coverage:
            w = DOMAIN_WEIGHTS.get(dc.domain, 0.05)
            weighted_sum += dc.radar_value * w
            weight_sum += w

        base_score = weighted_sum / weight_sum if weight_sum > 0 else 0.0

        # Apply gap penalties
        critical_penalty = min(0.4, len(critical_gaps) * 0.08)
        major_penalty = min(0.2, len(major_gaps) * 0.03)

        final_score = max(0.0, base_score - critical_penalty - major_penalty)
        return round(final_score, 4)

    def _readiness_label(self, score: float) -> str:
        if score >= 0.85:
            return "Role-Ready"
        elif score >= 0.70:
            return "Near-Ready"
        elif score >= 0.50:
            return "Developing"
        elif score >= 0.30:
            return "Early Stage"
        else:
            return "Significant Gap"

    async def _generate_reasoning_trace(
        self,
        resume_data: Dict,
        jd_data: Dict,
        critical_gaps: List[SkillGap],
        major_gaps: List[SkillGap],
        readiness_score: float,
    ) -> str:
        candidate_skills = [s.get("name", "") for s in resume_data.get("skills", [])[:15]]
        critical_names = [g.skill_name for g in critical_gaps[:5]]
        major_names = [g.skill_name for g in major_gaps[:5]]

        prompt = GAP_REASONING_PROMPT.format(
            candidate_skills=", ".join(candidate_skills) or "None identified",
            years_exp=resume_data.get("years_of_experience", "Unknown"),
            current_role=resume_data.get("current_role", "Unknown"),
            target_role=jd_data.get("target_role", "Target Role"),
            critical_gaps=", ".join(critical_names) or "None",
            major_gaps=", ".join(major_names) or "None",
            readiness_pct=int(readiness_score * 100),
        )

        try:
            response = await self.llm.chat.completions.create(
                model=settings.GROQ_PRIMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise talent development analyst. Be professional, concise, and data-driven."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("gap.reasoning.failed", error=str(e))
            return (
                f"Gap analysis complete. Overall readiness: {int(readiness_score*100)}%. "
                f"Critical gaps: {len(critical_gaps)}. Major gaps: {len(major_gaps)}. "
                f"Structured learning path generated to address deficiencies."
            )


_gap_engine: Optional[GapAnalysisEngine] = None


def get_gap_engine() -> GapAnalysisEngine:
    global _gap_engine
    if _gap_engine is None:
        _gap_engine = GapAnalysisEngine()
    return _gap_engine
