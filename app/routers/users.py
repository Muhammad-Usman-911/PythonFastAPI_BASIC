"""/users endpoints: the logged-in user's profile, plus an admin-only list."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.responses import ERROR_RESPONSES, ApiResponse, Page, ok
from app.deps import CurrentUser, DbSession, PaginationDep, require_role
from app.models.user import User
from app.schemas.user import ChangePasswordIn, UserOut, UserUpdate
from app.services import email_service, user_service

router = APIRouter(prefix="/users", tags=["users"], responses=ERROR_RESPONSES)


@router.get("/me", response_model=ApiResponse[UserOut])
def read_me(user: CurrentUser):
    """The logged-in user. Needs `Authorization: Bearer <access_token>`."""
    return ok(user)


@router.patch("/me", response_model=ApiResponse[UserOut])
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession):
    return ok(user_service.update_profile(db, user, data), "Profile updated")


@router.post("/me/change-password", response_model=ApiResponse[None])
def change_password(data: ChangePasswordIn, user: CurrentUser, db: DbSession, background: BackgroundTasks):
    user_service.change_password(db, user, data)
    background.add_task(email_service.send_password_changed, user.email)
    return ok(None, "Password changed")


@router.get("", response_model=ApiResponse[Page[UserOut]])
def list_users(
    db: DbSession,
    page: PaginationDep,
    _admin: Annotated[User, Depends(require_role("admin"))],
):
    """Admin only: example of a role-protected, paginated list endpoint."""
    users, total = user_service.list_users(db, page.limit, page.offset)
    return ok({"items": users, "total": total, "limit": page.limit, "offset": page.offset})
