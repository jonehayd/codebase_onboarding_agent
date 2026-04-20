import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _STATUS_CODES.get(exc.status_code, "ERROR")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    if exc.status_code >= 500:
        logger.error("%s %s -> %d: %s", request.method, request.url.path, exc.status_code, message)
    else:
        logger.warning("%s %s -> %d: %s", request.method, request.url.path, exc.status_code, message)
    return JSONResponse(status_code=exc.status_code, content=_error_body(code, message))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    message = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    logger.warning("%s %s -> 422: %s", request.method, request.url.path, message)
    return JSONResponse(status_code=422, content=_error_body("VALIDATION_ERROR", message))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred"),
    )


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("%s %s -> 429: rate limit exceeded (%s)", request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=429,
        content=_error_body("RATE_LIMITED", f"Rate limit exceeded: {exc.detail}"),
    )
