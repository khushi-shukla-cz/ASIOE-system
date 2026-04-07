"""
ASIOE — Pydantic Schemas
Full type-safe API contract definitions.
Used for request validation, response serialization, and OpenAPI docs.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillDomain(str, Enum):
    TECHNICAL = "technical"
    ANALYTICAL = "analytical"
    LEADERSHIP = "leadership"
    COMMUNICATION = "communication"
    DOMAIN_SPECIFIC = "domain_specific"
    OPERATIONAL = "operational"
    SOFT_SKILLS = "soft_skills"


class SessionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GapSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NONE = "none"


# ── Skill Models ───────────────────────────────────────────────────────────────

class ExtractedSkill(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    name: str
    canonical_name: Optional[str] = None
    domain: SkillDomain
    proficiency_level: DifficultyLevel
    proficiency_score: float = Field(ge=0.0, le=1.0)
    years_used: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")
    source: str = Field(description="resume | jd_required | jd_preferred")
    context_snippet: Optional[str] = None


class NormalizedSkill(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    canonical_name: str
    aliases: List[str] = []
    domain: SkillDomain
    onet_code: Optional[str] = None
    difficulty_level: DifficultyLevel
    avg_time_to_learn_hours: float
    importance_score: float = Field(ge=0.0, le=1.0)
    prerequisites: List[str] = []


# ── Gap Analysis Models ────────────────────────────────────────────────────────

class SkillGap(BaseModel):
    skill_id: str
    skill_name: str
    domain: SkillDomain
    severity: GapSeverity
    current_score: float = Field(ge=0.0, le=1.0, description="Candidate's current level")
    required_score: float = Field(ge=0.0, le=1.0, description="Role requirement level")
    gap_delta: float
    reasoning: str


class DomainCoverage(BaseModel):
    domain: SkillDomain
    coverage_percentage: float = Field(ge=0.0, le=100.0)
    matched_skills: int
    total_required: int
    radar_value: float


class GapAnalysisResult(BaseModel):
    session_id: str
    overall_readiness_score: float = Field(ge=0.0, le=1.0)
    readiness_label: str
    critical_gaps: List[SkillGap]
    major_gaps: List[SkillGap]
    minor_gaps: List[SkillGap]
    strength_areas: List[Dict[str, Any]]
    domain_coverage: List[DomainCoverage]
    reasoning_trace: str
    analysis_timestamp: datetime


# ── Learning Path Models ───────────────────────────────────────────────────────

class LearningModule(BaseModel):
    module_id: str
    skill_id: str
    skill_name: str
    title: str
    description: str
    domain: SkillDomain
    difficulty_level: DifficultyLevel
    estimated_hours: float
    sequence_order: int
    phase_number: int

    # Course reference
    course_id: Optional[str] = None
    course_title: Optional[str] = None
    course_url: Optional[str] = None
    course_provider: Optional[str] = None

    # Graph relationships
    prerequisite_module_ids: List[str] = []
    unlocks_module_ids: List[str] = []

    # Explainability
    why_selected: str
    dependency_chain: List[str]
    importance_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)


class PathPhase(BaseModel):
    phase_number: int
    phase_name: str
    description: str
    modules: List[LearningModule]
    estimated_hours: float
    estimated_weeks: float
    focus_domains: List[str]


class LearningPathResult(BaseModel):
    session_id: str
    path_id: str
    target_role: str

    phases: List[PathPhase]
    total_modules: int
    total_hours: float
    total_weeks: float

    path_graph: Dict[str, Any]  # Nodes + edges for D3 visualization

    efficiency_score: float
    redundancy_eliminated: int  # Number of known skills skipped
    path_algorithm: str
    path_version: int

    reasoning_trace: str
    generated_at: datetime


# ── Explainability Models ──────────────────────────────────────────────────────

class NodeExplanation(BaseModel):
    node_id: str
    skill_name: str
    why_included: str
    dependency_chain: List[str]
    confidence_score: float
    importance_rank: int
    gap_contribution: float
    alternative_paths: List[str] = []


class SystemReasoningTrace(BaseModel):
    session_id: str
    parsing_trace: str
    normalization_trace: str
    gap_trace: str
    path_trace: str
    total_tokens_used: int
    model_used: str
    generated_at: datetime


# ── API Request/Response ───────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    jd_text: str = Field(..., min_length=50, max_length=10000)
    target_role: Optional[str] = None
    priority_mode: str = Field(
        default="balanced",
        pattern="^(speed|balanced|thoroughness)$"
    )
    max_modules: int = Field(default=20, ge=5, le=50)
    time_constraint_weeks: Optional[int] = Field(default=None, ge=1, le=104)

    @field_validator("jd_text")
    @classmethod
    def clean_jd_text(cls, v: str) -> str:
        return v.strip()


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    target_role: Optional[str] = None


class AnalysisCompleteResponse(BaseModel):
    session_id: str
    status: SessionStatus
    skill_profile: Optional[Dict[str, Any]] = None
    gap_analysis: Optional[GapAnalysisResult] = None
    learning_path: Optional[LearningPathResult] = None
    reasoning_trace: Optional[SystemReasoningTrace] = None
    processing_time_ms: float


class SimulationRequest(BaseModel):
    session_id: str
    time_constraint_weeks: int = Field(..., ge=1, le=104)
    max_modules: Optional[int] = Field(default=None, ge=5, le=50)
    priority_domains: List[str] = []
    exclude_module_ids: List[str] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, bool]
