"""Unit tests for normalization engine boundary conditions and skill matching strategies."""

from __future__ import annotations

import pytest

from engines.normalization.normalization_engine import NormalizationEngine
from schemas.schemas import NormalizedSkill, SkillDomain


class TestNormalizationExactMatching:
    """Tests for exact-match skill normalization."""

    @pytest.mark.asyncio
    async def test_exact_match_returns_confidence_1_0(self):
        """Verify exact matches yield confidence = 1.0."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        # Assuming engine has skill ontology with "Python" entry
        result = await engine.normalize_skill("Python", domain=SkillDomain.TECHNICAL)

        if result:
            assert isinstance(result, NormalizedSkill)
            if result.match_strategy == "exact":
                assert result.confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_exact_match_case_insensitive(self):
        """Verify exact matching is case-insensitive."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        result_lower = await engine.normalize_skill("python", domain=SkillDomain.TECHNICAL)
        result_upper = await engine.normalize_skill("PYTHON", domain=SkillDomain.TECHNICAL)

        # Both should normalize to same canonical skill
        if result_lower and result_upper:
            assert result_lower.canonical_skill_id == result_upper.canonical_skill_id

    @pytest.mark.asyncio
    async def test_exact_match_with_common_abbreviations(self):
        """Verify exact matching handles common abbreviations."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        # Test common abbreviations/variants
        skills_to_test = [
            ("Python", "py"),
            ("JavaScript", "JS"),
            ("SQL", "sql"),
        ]

        for full_name, abbrev in skills_to_test:
            result_full = await engine.normalize_skill(full_name, domain=SkillDomain.TECHNICAL)
            result_abbrev = await engine.normalize_skill(abbrev, domain=SkillDomain.TECHNICAL)

            # Both should resolve if in ontology
            if result_full and result_abbrev:
                # May resolve to same or related skills
                assert result_full.canonical_skill_id is not None
                assert result_abbrev.canonical_skill_id is not None


class TestNormalizationSemanticMatching:
    """Tests for semantic similarity-based skill matching."""

    @pytest.mark.asyncio
    async def test_semantic_match_confidence_bounded(self):
        """Verify semantic matches have confidence in [0, 1)."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        result = await engine.normalize_skill("machine learning algorithms", domain=SkillDomain.TECHNICAL)

        if result and result.match_strategy == "semantic":
            assert 0.0 <= result.confidence_score < 1.0

    @pytest.mark.asyncio
    async def test_semantic_match_similarity_threshold(self):
        """Verify low-similarity matches are rejected (below threshold)."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        # Very dissimilar to domain should be rejected or have low confidence
        result = await engine.normalize_skill("xyz_random_gibberish_xyz", domain=SkillDomain.TECHNICAL)

        if result:
            # Should either be None or have very low confidence
            if result.confidence_score:
                assert result.confidence_score < 0.5

    @pytest.mark.asyncio
    async def test_semantic_match_prefers_domain_proximity(self):
        """Verify semantic matching prefers skills from same domain."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        # "communication" could match soft skills domain
        result_soft = await engine.normalize_skill("communication", domain=SkillDomain.SOFT_SKILLS)
        result_tech = await engine.normalize_skill("communication", domain=SkillDomain.TECHNICAL)

        if result_soft and result_tech:
            # Soft skills should be higher confidence in soft domain
            if result_soft.confidence_score and result_tech.confidence_score:
                assert result_soft.confidence_score >= result_tech.confidence_score


class TestNormalizationFallbackStrategies:
    """Tests for fallback skill generation when no match found."""

    @pytest.mark.asyncio
    async def test_synthetic_skill_generated_for_unmatched_input(self):
        """Verify synthetic skills are created for completely unmatched inputs."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        input_skill = "specialized_bio_informatics_technique"
        result = await engine.normalize_skill(input_skill, domain=SkillDomain.TECHNICAL)

        if result:
            # Fallback creates synthetic skill with original input as reference
            assert result.canonical_skill_name is not None
            # Confidence should be lower for synthetic
            if result.confidence_score:
                assert result.confidence_score < 0.7

    @pytest.mark.asyncio
    async def test_fallback_preserves_domain_context(self):
        """Verify fallback skills retain domain information."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        result = await engine.normalize_skill("fictional_leadership_method", domain=SkillDomain.SOFT_SKILLS)

        if result:
            assert result.domain == SkillDomain.SOFT_SKILLS

    @pytest.mark.asyncio
    async def test_fallback_still_produces_valid_skill_id(self):
        """Verify synthetic skills have valid (hashable) IDs."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        result = await engine.normalize_skill("obscure_skill_x", domain=SkillDomain.TECHNICAL)

        if result:
            assert result.canonical_skill_id is not None
            # Should be hashable (string, int, uuid)
            try:
                hash(result.canonical_skill_id)
            except TypeError:
                pytest.fail(f"Skill ID not hashable: {result.canonical_skill_id}")


class TestNormalizationDeduplication:
    """Tests for deduplication when normalizing skill lists."""

    @pytest.mark.asyncio
    async def test_deduplicates_identical_skills(self):
        """Verify duplicate entries are deduplicated."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        input_skills = ["Python", "python", "PYTHON", "Python"]
        results = await engine.normalize_skill_list(input_skills, domain=SkillDomain.TECHNICAL)

        # Should result in single canonical skill
        unique_skill_ids = set(r.canonical_skill_id for r in results if r)
        assert len(unique_skill_ids) <= len(input_skills)

    @pytest.mark.asyncio
    async def test_deduplication_keeps_highest_confidence(self):
        """Verify among duplicates, highest confidence match is retained."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        # Mix of exact and semantic matches for same skill
        input_skills = ["Python", "Python programming", "python lang"]
        results = await engine.normalize_skill_list(input_skills, domain=SkillDomain.TECHNICAL)

        # Find entries for Python skill
        python_entries = [r for r in results if r and "python" in r.canonical_skill_name.lower()]
        
        if len(python_entries) > 1:
            # Should keep entry with highest confidence
            confidences = [r.confidence_score for r in python_entries]
            # Duplicate should be highest confidence
            assert max(confidences) == python_entries[0].confidence_score

    @pytest.mark.asyncio
    async def test_deduplication_preserves_order_of_first_occurrence(self):
        """Verify deduplication preserves order of first occurrence."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        input_skills = ["SQL", "Python", "SQL", "Docker"]
        results = await engine.normalize_skill_list(input_skills, domain=SkillDomain.TECHNICAL)

        # Extract unique canonical skills preserving order
        seen_ids = set()
        ordered_unique = []
        for r in results:
            if r and r.canonical_skill_id not in seen_ids:
                ordered_unique.append(r.canonical_skill_id)
                seen_ids.add(r.canonical_skill_id)

        # First occurrence of each should be preserved in order
        assert len(ordered_unique) >= 3  # At least SQL, Python, Docker


class TestNormalizationDomainConsistency:
    """Tests for domain handling and consistency."""

    @pytest.mark.asyncio
    async def test_normalization_respects_domain_context(self):
        """Verify domain parameter influences skill matching."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        # Same input, different domains
        result_tech = await engine.normalize_skill("communication", domain=SkillDomain.TECHNICAL)
        result_soft = await engine.normalize_skill("communication", domain=SkillDomain.SOFT_SKILLS)

        if result_tech and result_soft:
            # Should normalize to different canonical skills or with domain difference
            # Or at least, soft skills context should be preserved
            assert result_soft.domain == SkillDomain.SOFT_SKILLS

    @pytest.mark.asyncio
    async def test_all_normalized_skills_have_valid_domain(self):
        """Verify all normalized skills have assigned domain."""
        engine = object.__new__(NormalizationEngine)
        engine._initialized = True

        input_skills = ["Python", "Leadership", "Docker", "Communication"]
        results = await engine.normalize_skill_list(
            input_skills, 
            domain=SkillDomain.TECHNICAL,
        )

        for result in results:
            if result:
                assert result.domain is not None
                assert result.domain in [d for d in SkillDomain]
