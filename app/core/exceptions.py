"""Central error handling: every error leaves the API in the same envelope.

Node equivalent: an Express error middleware `app.use((err, req, res, next) => ...)`
or a NestJS exception filter.

How to use it:
    from app.core.exceptions import NotFoundError
    raise NotFoundError("User not found")
    raise ConflictError("Email already registered", code="email_taken")
    raise BadRequestError("Bad file", details={"max_mb": 10})

You never write try/except just to send an error response. Raise, and the handlers
below turn it into:
    {"success": false, "message": "User not found",
     "error": {"code": "not_found", "details": null, "request_id": "a1b2c3d4"}}

Four handlers cover every possible error:
1. AppError                -> our own errors, with their status and code
2. RequestValidationError  -> bad body / query / path params (422, with per-field details)
3. StarletteHTTPException  -> FastAPI/Starlette's own errors (unknown route 404, 405, ...)
4. Exception               -> anything unexpected: logged with traceback, generic 500 to the client
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_body

logger = logging.getLogger("app")


# ---------------------------------------------------------------------------
# Error classes: raise these from anywhere
# ---------------------------------------------------------------------------
class AppError(Exception):
    """Base class. Subclasses set the default status_code and code."""

    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code  # override per raise, e.g. code="email_taken"
        self.details = details


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"


# Default codes for HTTP errors raised by FastAPI itself (or by `raise HTTPException`).
_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    429: "too_many_requests",
}


def _request_id(request: Request) -> str | None:
    # Set by the request-id middleware (app/core/middleware.py).
    return getattr(request.state, "request_id", None)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.message, exc.code, exc.details, _request_id(request)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Turn Pydantic's error list into something a frontend can show next to each field:
        # [{"field": "body.email", "message": "value is not a valid email address"}]
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())),
                # Pydantic prefixes messages from our validators with "Value error, ".
                "message": str(err.get("msg", "Invalid value")).removeprefix("Value error, "),
                "type": err.get("type"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                error_body("Validation failed", "validation_error", details, _request_id(request))
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                message, _HTTP_CODES.get(exc.status_code, "http_error"), None, _request_id(request)
            ),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback for us; never send internals to the client.
        logger.exception("Unhandled error [%s] %s %s", _request_id(request), request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_body("Something went wrong", "internal_error", None, _request_id(request)),
        )
