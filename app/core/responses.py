"""The ONE response shape every endpoint uses.

Success:  {"success": true,  "message": "...", "data": {...}}
Error:    {"success": false, "message": "...", "error": {"code": "...", "details": ..., "request_id": "..."}}

Why an envelope? The frontend can handle every response the same way:
`if (!res.success) showToast(res.message)` and otherwise read `res.data`.

How to use it in a route (see app/routers/*.py):

    @router.get("/me", response_model=ApiResponse[UserOut])
    def me(user: CurrentUser):
        return ok(user)                        # -> {"success": true, "data": {...user}}

    @router.post("/things", response_model=ApiResponse[ThingOut], status_code=201)
    def create(...):
        return ok(thing, "Thing created")

`response_model=ApiResponse[UserOut]` does two jobs: Swagger shows the exact shape,
and FastAPI filters the data through UserOut, so fields that are not declared there
(e.g. hashed_password) can never leak.

Errors are NOT built here by hand. Raise an AppError subclass anywhere
(router, service, dependency) and app/core/exceptions.py builds the error envelope.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Success envelope. `T` is the schema of `data` (shown in Swagger)."""

    success: bool = True
    message: str | None = None
    data: T | None = None


class ErrorInfo(BaseModel):
    code: str = Field(examples=["not_found"])
    details: Any | None = Field(
        default=None, description="Extra info, e.g. the list of invalid fields for validation errors"
    )
    request_id: str | None = Field(
        default=None, description="Matches the X-Request-ID header and the log line"
    )


class ErrorResponse(BaseModel):
    """Error envelope. Used for Swagger docs; the handlers build the same shape."""

    success: bool = False
    message: str = Field(examples=["User not found"])
    error: ErrorInfo


class Page(BaseModel, Generic[T]):
    """Use as `ApiResponse[Page[ItemOut]]` for list endpoints."""

    items: list[T]
    total: int
    limit: int
    offset: int


def ok(data: Any = None, message: str | None = None) -> dict[str, Any]:
    """Build a success envelope. FastAPI validates it against the route's response_model."""
    return {"success": True, "message": message, "data": data}


def error_body(message: str, code: str, details: Any = None, request_id: str | None = None) -> dict[str, Any]:
    """Build an error envelope (used by the exception handlers)."""
    return {
        "success": False,
        "message": message,
        "error": {"code": code, "details": details, "request_id": request_id},
    }


# Shortcut to document common error responses on a router or route:
#   APIRouter(responses=ERROR_RESPONSES)
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    401: {"model": ErrorResponse, "description": "Not authenticated / invalid token"},
    403: {"model": ErrorResponse, "description": "Not allowed"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict (e.g. already exists)"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    429: {"model": ErrorResponse, "description": "Too many requests"},
}
