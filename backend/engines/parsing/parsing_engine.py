"""
ASIOE — Parsing Engine
Production-grade document parsing pipeline.

Flow:
1. Raw file → text extraction (PyMuPDF / pdfplumber)
2. Text cleaning and section segmentation
3. LLM-structured extraction (Groq / Llama-3.3-70B)
4. Pydantic schema validation + confidence scoring
5. Return typed ParsedDocument
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pdfplumber
import structlog
from groq import AsyncGroq

from core.config import settings
from engines.instrumentation import trace_engine_operation

logger = structlog.get_logger(__name__)


# ── Prompt Templates ───────────────────────────────────────────────────────────

RESUME_EXTRACTION_PROMPT = """You are an expert HR data analyst with 15 years of experience.
Extract structured information from this resume text with HIGH PRECISION.

RESUME TEXT:
{resume_text}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "candidate_name": "string or null",
  "candidate_email": "string or null",
  "current_role": "string or null",
  "years_of_experience": float or null,
  "education_level": "high_school|associate|bachelor|master|phd|bootcamp|self_taught|other or null",
  "skills": [
    {{
      "name": "exact skill name",
      "proficiency_level": "beginner|intermediate|advanced|expert",
      "proficiency_score": 0.0-1.0,
      "years_used": float or null,
      "domain": "technical|analytical|leadership|communication|domain_specific|operational|soft_skills",
      "confidence": 0.0-1.0,
      "context_snippet": "brief text from resume showing this skill"
    }}
  ],
  "work_experience": [
    {{
      "title": "job title",
      "company": "company name",
      "duration_years": float,
      "responsibilities": ["key responsibility 1", "key responsibility 2"]
    }}
  ],
  "certifications": ["cert1", "cert2"],
  "parsing_confidence": 0.0-1.0
}}

Rules:
- proficiency_score: 0.2=beginner, 0.4=intermediate, 0.7=advanced, 0.9=expert
- Be conservative with confidence scores
- Extract ALL technical skills, tools, frameworks, methodologies
- domain must exactly match one of the enum values
"""

JD_EXTRACTION_PROMPT = """You are an expert job requirements analyst.
Extract ALL required and preferred skills from this job description.

JOB DESCRIPTION:
{jd_text}

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "target_role": "inferred job title",
  "target_domain": "technical|operational|leadership|analytical|other",
  "required_skills": [
    {{
      "name": "skill name",
      "proficiency_level": "beginner|intermediate|advanced|expert",
      "proficiency_score": 0.0-1.0,
      "domain": "technical|analytical|leadership|communication|domain_specific|operational|soft_skills",
      "importance": "must_have|should_have|nice_to_have",
      "confidence": 0.0-1.0
    }}
  ],
  "preferred_skills": [
    {{
      "name": "skill name",
      "proficiency_level": "beginner|intermediate|advanced|expert",
      "proficiency_score": 0.0-1.0,
      "domain": "technical|analytical|leadership|communication|domain_specific|operational|soft_skills",
      "confidence": 0.0-1.0
    }}
  ],
  "minimum_years_experience": float or null,
  "education_requirement": "string or null",
  "parsing_confidence": 0.0-1.0
}}
"""


# ── Text Extraction Utilities ──────────────────────────────────────────────────

class TextExtractor:
    """Multi-strategy text extraction from PDF/DOCX files."""

    @staticmethod
    def extract_from_pdf_bytes(file_bytes: bytes) -> Tuple[str, float]:
        """
        Try PyMuPDF first (fastest, best layout), fall back to pdfplumber.
        Returns (text, confidence_score).
        """
        # Strategy 1: PyMuPDF
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages_text = []
            for page in doc:
                text = page.get_text("text")
                pages_text.append(text)
            doc.close()
            full_text = "\n".join(pages_text).strip()
            if len(full_text) > 200:
                logger.debug("parser.pdf.pymupdf.success", chars=len(full_text))
                return full_text, 0.95
        except Exception as e:
            logger.warning("parser.pdf.pymupdf.failed", error=str(e))

        # Strategy 2: pdfplumber (handles complex layouts better)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
            full_text = "\n".join(pages_text).strip()
            if len(full_text) > 200:
                logger.debug("parser.pdf.pdfplumber.success", chars=len(full_text))
                return full_text, 0.85
        except Exception as e:
            logger.warning("parser.pdf.pdfplumber.failed", error=str(e))

        return "", 0.0

    @staticmethod
    def extract_from_docx_bytes(file_bytes: bytes) -> Tuple[str, float]:
        """Extract text from DOCX using python-docx."""
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n".join(paragraphs)
            return full_text, 0.95
        except Exception as e:
            logger.warning("parser.docx.failed", error=str(e))
            return "", 0.0

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Normalize extracted text for LLM consumption."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', raw_text)
        text = re.sub(r' {3,}', ' ', text)
        # Remove non-printable characters
        text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
        # Limit to reasonable length (avoid token overflow)
        if len(text) > 8000:
            text = text[:8000] + "\n[TRUNCATED]"
        return text.strip()


# ── LLM Extraction Client ──────────────────────────────────────────────────────

class LLMExtractor:
    """Groq-backed structured extraction with retry logic."""

    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.primary_model = settings.GROQ_PRIMARY_MODEL
        self.fallback_model = settings.GROQ_FALLBACK_MODEL

    async def extract_structured(
        self,
        prompt: str,
        context: str = "",
    ) -> Tuple[Dict[str, Any], int, int]:
        """
        Call Groq API with retry logic.
        Returns (parsed_json, input_tokens, output_tokens).
        """
        for attempt in range(settings.GROQ_MAX_RETRIES):
            model = self.primary_model if attempt < 2 else self.fallback_model
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precise data extraction system. "
                                "Always return valid JSON only. No markdown. "
                                "No explanation. No preamble."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=settings.GROQ_TEMPERATURE,
                    max_tokens=settings.GROQ_MAX_TOKENS,
                    timeout=settings.GROQ_TIMEOUT_SECONDS,
                )

                raw = response.choices[0].message.content.strip()
                # Strip any accidental markdown fences
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)

                parsed = json.loads(raw)
                usage = response.usage
                return parsed, usage.prompt_tokens, usage.completion_tokens

            except json.JSONDecodeError as e:
                logger.warning(
                    "parser.llm.json_error",
                    attempt=attempt,
                    error=str(e),
                )
                if attempt == settings.GROQ_MAX_RETRIES - 1:
                    raise
            except Exception as e:
                logger.error("parser.llm.error", attempt=attempt, error=str(e))
                if attempt == settings.GROQ_MAX_RETRIES - 1:
                    raise
                await _async_sleep(1.5 ** attempt)

        return {}, 0, 0


async def _async_sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)


# ── Main Parsing Engine ────────────────────────────────────────────────────────

class ParsingEngine:
    """
    Orchestrates the full parsing pipeline:
    file bytes → clean text → LLM extraction → typed result
    """

    def __init__(self) -> None:
        self.extractor = TextExtractor()
        self.llm = LLMExtractor()

    @trace_engine_operation("parsing", "parse_resume")
    async def parse_resume(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """
        Parse a resume file and extract structured skill data.
        Returns typed ParsedResume dict.
        """
        start = time.perf_counter()
        ext = Path(filename).suffix.lower()

        # Step 1: Extract raw text
        if ext == ".pdf":
            raw_text, extraction_conf = self.extractor.extract_from_pdf_bytes(file_bytes)
        elif ext in (".docx", ".doc"):
            raw_text, extraction_conf = self.extractor.extract_from_docx_bytes(file_bytes)
        elif ext == ".txt":
            raw_text = file_bytes.decode("utf-8", errors="replace")
            extraction_conf = 0.99
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if not raw_text:
            raise ValueError("Could not extract text from resume file")

        # Step 2: Clean text
        clean_text = self.extractor.clean_text(raw_text)

        # Step 3: LLM structured extraction
        prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=clean_text)
        parsed, in_tokens, out_tokens = await self.llm.extract_structured(prompt)

        # Step 4: Validate and enrich
        result = self._validate_resume_extraction(parsed, extraction_conf)
        result["file_hash"] = hashlib.sha256(file_bytes).hexdigest()
        result["processing_ms"] = int((time.perf_counter() - start) * 1000)
        result["input_tokens"] = in_tokens
        result["output_tokens"] = out_tokens

        logger.info(
            "parser.resume.complete",
            skills_found=len(result.get("skills", [])),
            confidence=result.get("parsing_confidence"),
            ms=result["processing_ms"],
        )
        return result

    @trace_engine_operation("parsing", "parse_jd")
    async def parse_jd(self, jd_text: str) -> Dict[str, Any]:
        """Parse a job description and extract required/preferred skills."""
        start = time.perf_counter()

        clean_text = self.extractor.clean_text(jd_text)
        prompt = JD_EXTRACTION_PROMPT.format(jd_text=clean_text)
        parsed, in_tokens, out_tokens = await self.llm.extract_structured(prompt)

        result = self._validate_jd_extraction(parsed)
        result["jd_hash"] = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
        result["processing_ms"] = int((time.perf_counter() - start) * 1000)
        result["input_tokens"] = in_tokens
        result["output_tokens"] = out_tokens

        logger.info(
            "parser.jd.complete",
            required=len(result.get("required_skills", [])),
            preferred=len(result.get("preferred_skills", [])),
            ms=result["processing_ms"],
        )
        return result

    # ── Validation Helpers ─────────────────────────────────────────────────────

    def _validate_resume_extraction(
        self, raw: Dict[str, Any], extraction_conf: float
    ) -> Dict[str, Any]:
        valid_domains = {
            "technical", "analytical", "leadership",
            "communication", "domain_specific", "operational", "soft_skills"
        }
        valid_levels = {"beginner", "intermediate", "advanced", "expert"}

        skills = raw.get("skills", [])
        validated_skills = []
        for skill in skills:
            if not skill.get("name"):
                continue
            # Normalize domain
            domain = skill.get("domain", "technical")
            if domain not in valid_domains:
                domain = "technical"
            # Normalize level
            level = skill.get("proficiency_level", "intermediate")
            if level not in valid_levels:
                level = "intermediate"
            # Clamp scores
            skill["domain"] = domain
            skill["proficiency_level"] = level
            skill["proficiency_score"] = max(0.0, min(1.0, float(skill.get("proficiency_score", 0.5))))
            skill["confidence"] = max(0.0, min(1.0, float(skill.get("confidence", 0.7))))
            validated_skills.append(skill)

        raw["skills"] = validated_skills
        raw["parsing_confidence"] = min(
            extraction_conf,
            float(raw.get("parsing_confidence", 0.8))
        )
        return raw

    def _validate_jd_extraction(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        valid_domains = {
            "technical", "analytical", "leadership",
            "communication", "domain_specific", "operational", "soft_skills"
        }
        for skill_list_key in ("required_skills", "preferred_skills"):
            skills = raw.get(skill_list_key, [])
            validated = []
            for skill in skills:
                if not skill.get("name"):
                    continue
                domain = skill.get("domain", "technical")
                if domain not in valid_domains:
                    domain = "technical"
                skill["domain"] = domain
                skill["proficiency_score"] = max(0.0, min(1.0, float(skill.get("proficiency_score", 0.7))))
                skill["confidence"] = max(0.0, min(1.0, float(skill.get("confidence", 0.8))))
                validated.append(skill)
            raw[skill_list_key] = validated
        return raw


# ── Module-level singleton ─────────────────────────────────────────────────────
_parsing_engine: Optional[ParsingEngine] = None


def get_parsing_engine() -> ParsingEngine:
    global _parsing_engine
    if _parsing_engine is None:
        _parsing_engine = ParsingEngine()
    return _parsing_engine
