from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from core.errors import AppError, EngineExecutionError, ErrorCode, build_error_response


def _build_test_app() -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        request.state.correlation_id = request.headers.get("X-Correlation-ID", "test-correlation-id")
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return build_error_response(
            request=request,
            status_code=422,
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = ErrorCode.VALIDATION_ERROR if 400 <= exc.status_code < 500 else ErrorCode.INTERNAL_ERROR
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
            details={"status_code": exc.status_code},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(Exception)
    async def internal_exception_handler(request: Request, exc: Exception):
        return build_error_response(
            request=request,
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error",
            details={"error": str(exc)},
        )

    @app.get("/validation")
    async def validation_endpoint(limit: int):
        return {"limit": limit}

    @app.get("/engine")
    async def engine_endpoint():
        raise EngineExecutionError("Engine call failed", details={"engine": "path"})

    @app.get("/http")
    async def http_endpoint():
        raise HTTPException(status_code=404, detail="Missing resource")

    @app.get("/internal")
    async def internal_endpoint():
        raise RuntimeError("boom")

    return app


def _assert_error_shape(payload: dict):
    assert "code" in payload
    assert "message" in payload
    assert "details" in payload
    assert "correlation_id" in payload
    assert "timestamp" in payload
    assert "path" in payload


def test_validation_error_contract_shape_and_code():
    client = TestClient(_build_test_app())

    response = client.get("/validation", params={"limit": "not-an-int"}, headers={"X-Correlation-ID": "cid-123"})

    assert response.status_code == 422
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["correlation_id"] == "cid-123"
    assert payload["path"] == "/validation"


def test_engine_error_contract_shape_and_code():
    client = TestClient(_build_test_app())

    response = client.get("/engine", headers={"X-Correlation-ID": "cid-456"})

    assert response.status_code == 502
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["code"] == ErrorCode.ENGINE_ERROR.value
    assert payload["correlation_id"] == "cid-456"
    assert payload["details"]["engine"] == "path"


def test_http_error_contract_shape_and_code():
    client = TestClient(_build_test_app())

    response = client.get("/http", headers={"X-Correlation-ID": "cid-789"})

    assert response.status_code == 404
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["correlation_id"] == "cid-789"
    assert payload["details"]["status_code"] == 404


def test_internal_error_contract_shape_and_code():
    client = TestClient(_build_test_app())

    response = client.get("/internal", headers={"X-Correlation-ID": "cid-000"})

    assert response.status_code == 500
    payload = response.json()
    _assert_error_shape(payload)
    assert payload["code"] == ErrorCode.INTERNAL_ERROR.value
    assert payload["correlation_id"] == "cid-000"
    assert payload["path"] == "/internal"
