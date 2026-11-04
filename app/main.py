from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.routers import auth, tasks

app = FastAPI(title="Task API")

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
