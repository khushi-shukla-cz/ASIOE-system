from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    ENGINE_ERROR = "ENGINE_ERROR"
    INFRA_ERROR = "INFRA_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class EngineExecutionError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.ENGINE_ERROR,
            message=message,
            details=details,
            status_code=502,
        )


class InfraDependencyError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.INFRA_ERROR,
            message=message,
            details=details,
            status_code=503,
        )


class RequestTimeoutError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.TIMEOUT_ERROR,
            message=message,
            details=details,
            status_code=504,
        )


def build_error_payload(
    request: Request,
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    correlation_id = getattr(request.state, "correlation_id", None)
    return {
        "code": code.value,
        "message": message,
        "details": details or {},
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
    }


def build_error_response(
    request: Request,
    status_code: int,
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(request, code, message, details),
    )
