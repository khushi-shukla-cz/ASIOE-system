from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from core.config import settings


@dataclass
class AuthenticatedPrincipal:
    user_id: str


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode((encoded + padding).encode("ascii"))


def _sign(payload_segment: str) -> str:
    signature = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=payload_segment.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return _b64url_encode(signature)


def issue_session_token(session_id: str, user_id: str) -> str:
    exp = int(time.time()) + settings.SESSION_TOKEN_TTL_SECONDS
    payload = {"sid": session_id, "sub": user_id, "exp": exp}
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature_segment = _sign(payload_segment)
    return f"{payload_segment}.{signature_segment}"


def verify_session_token(token: str, session_id: str, user_id: str) -> None:
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token") from exc

    expected_signature = _sign(payload_segment)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token signature")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed session token payload") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session token expired")

    if payload.get("sid") != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session token does not match requested session")

    if payload.get("sub") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session token user mismatch")


def get_current_principal(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> AuthenticatedPrincipal:
    user_id = (x_user_id or "").strip()

    if settings.AUTH_ENABLED:
        allowed_keys = {k.strip() for k in settings.API_AUTH_KEYS.split(",") if k.strip()}
        if not x_api_key or x_api_key not in allowed_keys:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header is required")
    else:
        user_id = user_id or settings.DEFAULT_AUTH_USER

    return AuthenticatedPrincipal(user_id=user_id)


def require_session_access(
    session_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> AuthenticatedPrincipal:
    if not x_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Session-Token header is required",
        )

    verify_session_token(x_session_token, session_id=session_id, user_id=principal.user_id)

    return principal