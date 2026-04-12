from __future__ import annotations

import pytest
from fastapi import HTTPException

from core.auth import get_current_principal, issue_session_token, verify_session_token
from core.config import settings


def test_issue_and_verify_session_token_roundtrip():
    token = issue_session_token("session-1", "user-1")
    verify_session_token(token, session_id="session-1", user_id="user-1")


def test_verify_session_token_rejects_wrong_user():
    token = issue_session_token("session-1", "user-1")

    with pytest.raises(HTTPException) as exc:
        verify_session_token(token, session_id="session-1", user_id="user-2")

    assert exc.value.status_code == 403


def test_get_current_principal_requires_headers_when_auth_enabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_AUTH_KEYS", "k1,k2")

    principal = get_current_principal(x_api_key="k1", x_user_id="khushi")
    assert principal.user_id == "khushi"

    with pytest.raises(HTTPException) as exc:
        get_current_principal(x_api_key="invalid", x_user_id="khushi")

    assert exc.value.status_code == 401


def test_get_current_principal_defaults_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)
    monkeypatch.setattr(settings, "DEFAULT_AUTH_USER", "anonymous")

    principal = get_current_principal(x_api_key=None, x_user_id=None)
    assert principal.user_id == "anonymous"