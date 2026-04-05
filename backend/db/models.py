"""
ASIOE — ORM Models
Full relational schema for PostgreSQL.
Tracks sessions, analyses, skill profiles, and audit logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Analysis Session ───────────────────────────────────────────────────────────

class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending | processing | completed | failed

    resume_filename: Mapped[Optional[str]] = mapped_column(String(255))
    jd_text_hash: Mapped[Optional[str]] = mapped_column(String(64))
    target_role: Mapped[Optional[str]] = mapped_column(String(255))
    target_domain: Mapped[Optional[str]] = mapped_column(String(128))

    # Relationships
    skill_profile: Mapped[Optional["SkillProfile"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    gap_analysis: Mapped[Optional["GapAnalysis"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    learning_path: Mapped[Optional["LearningPath"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


# ── Skill Profile ──────────────────────────────────────────────────────────────

class SkillProfile(Base):
    __tablename__ = "skill_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Raw extracted data
    candidate_name: Mapped[Optional[str]] = mapped_column(String(255))
    candidate_email: Mapped[Optional[str]] = mapped_column(String(255))
    years_of_experience: Mapped[Optional[float]] = mapped_column(Float)
    education_level: Mapped[Optional[str]] = mapped_column(String(128))
    current_role: Mapped[Optional[str]] = mapped_column(String(255))

    # Structured skill data stored as JSONB
    extracted_skills: Mapped[Dict] = mapped_column(JSON, default=dict)
    # Format: {skill_id: {name, level, confidence, source}}

    normalized_skills: Mapped[Dict] = mapped_column(JSON, default=dict)
    # Format: {canonical_skill_id: {name, proficiency_score, embedding_cluster}}

    jd_required_skills: Mapped[Dict] = mapped_column(JSON, default=dict)
    jd_preferred_skills: Mapped[Dict] = mapped_column(JSON, default=dict)

    parsing_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extraction_model: Mapped[Optional[str]] = mapped_column(String(128))

    session: Mapped["AnalysisSession"] = relationship(back_populates="skill_profile")


# ── Gap Analysis ───────────────────────────────────────────────────────────────

class GapAnalysis(Base):
    __tablename__ = "gap_analyses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    overall_readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    # 0.0 → 1.0, represents candidate's readiness for the target role

    critical_gaps: Mapped[Dict] = mapped_column(JSON, default=list)
    major_gaps: Mapped[Dict] = mapped_column(JSON, default=list)
    # List of {skill_id, name, gap_severity, domain}

    minor_gaps: Mapped[Dict] = mapped_column(JSON, default=list)
    strength_areas: Mapped[Dict] = mapped_column(JSON, default=list)

    domain_coverage: Mapped[Dict] = mapped_column(JSON, default=dict)
    # {domain_name: coverage_percentage}

    gap_vectors: Mapped[Dict] = mapped_column(JSON, default=dict)
    # Cosine similarity vectors for radar chart

    session: Mapped["AnalysisSession"] = relationship(back_populates="gap_analysis")


# ── Learning Path ──────────────────────────────────────────────────────────────

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    total_modules: Mapped[int] = mapped_column(Integer, default=0)
    estimated_hours: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_weeks: Mapped[float] = mapped_column(Float, default=0.0)

    phases: Mapped[Dict] = mapped_column(JSON, default=list)
    # List of Phase objects with ordered modules

    path_graph: Mapped[Dict] = mapped_column(JSON, default=dict)
    # Serialized DAG for frontend visualization

    efficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    # Measures redundancy elimination

    path_algorithm: Mapped[str] = mapped_column(String(64), default="topological_dfs")
    path_version: Mapped[int] = mapped_column(Integer, default=1)

    session: Mapped["AnalysisSession"] = relationship(back_populates="learning_path")


# ── Audit Log ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE")
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    engine: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(128))
    duration_ms: Mapped[Optional[float]] = mapped_column(Float)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Dict] = mapped_column(JSON, default=dict)

    session: Mapped["AnalysisSession"] = relationship(back_populates="audit_logs")
