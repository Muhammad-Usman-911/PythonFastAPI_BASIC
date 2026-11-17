"""Entry point: builds the FastAPI app. Run with `uvicorn app.main:app --reload`.

Node equivalent of this file:
    const app = express()
    app.use(cors()); app.use(logger)
    app.use('/api/v1/auth', authRouter)
    app.use(errorHandler)
    app.listen(8000)
(uvicorn does the "listen" part.)
"""

import logging

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware
from app.core.responses import ApiResponse, ok
from app.routers import auth, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "Starter API with auth (password, email code, refresh tokens, email verification, "
            "password reset) and email.\n\n"
            "Every response is `{success, message, data}`; every error is "
            "`{success: false, message, error: {code, details, request_id}}`.\n\n"
            "**Try it:** register → read the code in the server console (or Mailpit) → verify-email → "
            "click **Authorize** and paste the `access_token`."
        ),
        # Hide the docs in production if the API is private:
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(auth.router, prefix=settings.API_PREFIX)
    app.include_router(users.router, prefix=settings.API_PREFIX)

    @app.get("/health", tags=["health"], response_model=ApiResponse[dict])
    def health():
        """Liveness + database check (use it for Docker/Render/Railway health checks)."""
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return ok({"status": "ok", "database": "ok", "environment": settings.ENVIRONMENT})

    return app


app = create_app()
