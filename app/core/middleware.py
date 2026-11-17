"""Middleware: code that runs around EVERY request.

Node equivalent: `app.use(cors())` and `app.use((req, res, next) => { ...; next() })`.
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger("app.request")


def register_middleware(app: FastAPI) -> None:
    # CORS: lets your frontend (React, Next.js, ...) call this API from the browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_and_logging(request: Request, call_next):
        # 1. before the route: give the request an id (reuse the caller's if sent)
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id  # the error handlers put it in error bodies
        start = time.perf_counter()

        # 2. run the rest of the app (like `next()` in Express, but you get the response back)
        response = await call_next(request)

        # 3. after the route: add headers and log one line
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
