import asyncio

import pytest

from engines.parsing.parsing_engine import LLMExtractor, ParsingEngine


def test_llm_extractor_falls_back_to_secondary_model_on_retries(monkeypatch):
    class _Usage:
        prompt_tokens = 11
        completion_tokens = 7

    class _Message:
        content = '{"ok": true}'

    class _Choice:
        message = _Message()

    class _Response:
        usage = _Usage()
        choices = [_Choice()]

    class _Completions:
        def __init__(self):
            self.models = []

        async def create(self, **kwargs):
            self.models.append(kwargs["model"])
            if len(self.models) < 3:
                raise RuntimeError("primary unavailable")
            return _Response()

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    class _Client:
        def __init__(self):
            self.chat = _Chat()

    extractor = object.__new__(LLMExtractor)
    extractor.client = _Client()
    extractor.primary_model = "primary"
    extractor.fallback_model = "fallback"

    parsed, in_tokens, out_tokens = asyncio.run(extractor.extract_structured(prompt="irrelevant"))

    assert parsed == {"ok": True}
    assert in_tokens == 11
    assert out_tokens == 7
    assert extractor.client.chat.completions.models == ["primary", "primary", "fallback"]


def test_parse_resume_raises_when_text_extraction_fails():
    class _Extractor:
        @staticmethod
        def extract_from_pdf_bytes(_file_bytes):
            return "", 0.0

        @staticmethod
        def clean_text(raw_text):
            return raw_text

    class _LLM:
        async def extract_structured(self, prompt, context=""):
            del prompt, context
            return {}, 0, 0

    engine = object.__new__(ParsingEngine)
    engine.extractor = _Extractor()
    engine.llm = _LLM()

    with pytest.raises(ValueError, match="Could not extract text from resume file"):
        asyncio.run(engine.parse_resume(file_bytes=b"dummy", filename="resume.pdf"))
