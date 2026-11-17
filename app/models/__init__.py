# Import every model here so Alembic (and the tests' create_all) can see them.
# Forgot to add a new model here? `alembic revision --autogenerate` won't find its table.
from app.models.otp import OtpCode, OtpPurpose  # noqa: F401
from app.models.user import User  # noqa: F401
