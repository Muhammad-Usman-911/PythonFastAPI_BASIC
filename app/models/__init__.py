# Import every model here so Alembic and create_all can see them.
from app.models.otp import OtpCode  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
