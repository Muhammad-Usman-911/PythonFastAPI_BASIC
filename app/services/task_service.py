from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


def list_tasks(
    db: Session, user_id: int, done: Optional[bool], limit: int, offset: int
) -> tuple[list[Task], int]:
    stmt = select(Task).where(Task.user_id == user_id)
    if done is not None:
        stmt = stmt.where(Task.done == done)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = list(db.scalars(stmt.order_by(Task.id).limit(limit).offset(offset)))
    return items, total


def get_task(db: Session, user_id: int, task_id: int) -> Optional[Task]:
    # Filtering by user_id means users can never read each other's tasks.
    return db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))


def create_task(db: Session, user_id: int, data: TaskCreate) -> Task:
    task = Task(user_id=user_id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, data: TaskUpdate) -> Task:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()
