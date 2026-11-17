"""Profile operations for the logged-in user, plus an admin list."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import ChangePasswordIn, UserUpdate


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    # exclude_unset: only the fields the client actually sent (true PATCH semantics)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: ChangePasswordIn) -> None:
    # Users created by email-code login have no password yet: they may set one directly.
    if user.hashed_password is not None and not verify_password(
        data.current_password or "", user.hashed_password
    ):
        raise BadRequestError("Current password is incorrect", code="wrong_password")
    user.hashed_password = hash_password(data.new_password)
    db.commit()


def list_users(db: Session, limit: int, offset: int) -> tuple[list[User], int]:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    return list(users), total
