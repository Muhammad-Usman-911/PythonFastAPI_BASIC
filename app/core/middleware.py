import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# "uvicorn.error" is already configured to print at INFO level
logger = logging.getLogger("uvicorn.error")


def register_middleware(app: FastAPI) -> None:
    # CORS: lets your frontend (React, etc.) call this API from the browser
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Runs on every request, like an Express middleware / Nest interceptor:
    # adds a request id + timing header and logs one line per request.
    @app.middleware("http")
    async def timing_and_logging(request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()

        response = await call_next(request)  # let the request reach the router

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
        logger.info(
            "[%s] %s %s -> %s (%.1f ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
