"""Database engine, session factory and the Base class for models.

Node equivalent: creating the Prisma client / TypeORM DataSource once at startup.

- `engine`       : the connection pool (one per app)
- `SessionLocal` : makes a Session = one "unit of work" (a request uses one)
- `Base`         : every model inherits from it, so Alembic can find all tables

The per-request session is provided by `get_db()` in app/deps.py.
"""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite needs this flag because FastAPI may use the connection from another thread.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

# expire_on_commit=False: objects stay readable after commit (handy when returning them).
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Predictable constraint names, so Alembic migrations are stable across databases.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
