from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.deps import get_current_user, get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import task_service

# Every route in this router requires a valid JWT (like @UseGuards on a controller)
router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


def get_task_or_404(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    task = task_service.get_task(db, user.id, task_id)
    if not task:
        raise NotFoundError("Task not found")
    return task


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    done: Optional[bool] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = task_service.list_tasks(db, user.id, done, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task: Task = Depends(get_task_or_404)):
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.create_task(db, user.id, data)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    data: TaskUpdate,
    task: Task = Depends(get_task_or_404),
    db: Session = Depends(get_db),
):
    return task_service.update_task(db, task, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task: Task = Depends(get_task_or_404), db: Session = Depends(get_db)):
    task_service.delete_task(db, task)
