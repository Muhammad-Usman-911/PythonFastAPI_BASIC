"""Dependencies: reusable things a route can ask for in its parameters.

Node equivalent:
- get_db            ~ attaching a DB client to `req` / a NestJS provider
- get_current_user  ~ an auth middleware that sets `req.user` / NestJS JwtAuthGuard
- require_role      ~ a roles middleware / NestJS RolesGuard + @Roles('admin')
- pagination_params ~ a NestJS Pipe that parses ?limit=&offset=

FastAPI calls these for you. A route just declares what it needs:

    def me(user: CurrentUser, db: DbSession): ...
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

# auto_error=False: we raise our own UnauthorizedError so the error uses our envelope.
# HTTPBearer also adds the "Authorize" button to Swagger (paste the access token).
bearer_scheme = HTTPBearer(auto_error=False)


# ---------- DB session: one per request, always closed ----------
def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db  # the route runs here
    finally:
        db.close()  # runs after the response, even if the route raised


DbSession = Annotated[Session, Depends(get_db)]


# ---------- Auth guard ----------
def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if creds is None:
        raise UnauthorizedError("Not authenticated", code="not_authenticated")
    user_id = decode_token(creds.credentials, "access")
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists", code="invalid_token")
    if not user.is_active:
        raise ForbiddenError("This account is disabled", code="account_disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------- Role guard ----------
def require_role(*roles: str):
    """Usage: `admin: Annotated[User, Depends(require_role("admin"))]`
    or protect a whole router: `APIRouter(dependencies=[Depends(require_role("admin"))])`."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to do this", code="insufficient_role")
        return user

    return checker


# ---------- Pagination ----------
@dataclass
class Pagination:
    limit: int
    offset: int


def pagination_params(
    limit: Annotated[int, Query(ge=1, le=100, description="Max items to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Items to skip")] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(pagination_params)]
