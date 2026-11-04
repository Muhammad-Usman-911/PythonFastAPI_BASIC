# How to make a project / Commands

1.```mkdir taskapi && cd taskapi```
2.```python3 -m venv venv``` - command creates a standalone, isolated Python environment inside a new folder named "venv"
3.```source venv/bin/activate``` - The source venv/bin/activate command turns on (activates) your Python virtual environment on Linux and macOS.
4.```pip install "fastapi[standard]"```
5.```pip freeze > requirements.txt``` - The pip freeze > requirements.txt command saves a list of all installed Python packages and their exact versions into a text file named requirements.txt.
6.```mkdir app```
7.```touch app/__init__.py app/main.py```


# Task API (FastAPI + PostgreSQL/Supabase)

A small backend with:

- CRUD for tasks (each task belongs to a user)
- Passwordless login with an email OTP (6-digit code) and JWT
- PostgreSQL (Supabase) with SQLAlchemy and Alembic migrations
- Request validation, pagination, and a global error handler
- Automatic Swagger docs at `/docs`

---

## Project structure

```
taskapi/
├── app/
│   ├── main.py              # creates the app, registers routers + error handlers
│   ├── deps.py              # get_db and get_current_user (the "guard")
│   ├── core/
│   │   ├── config.py        # settings read from .env
│   │   ├── database.py      # engine, session, Base
│   │   ├── security.py      # OTP hashing, JWT create/decode
│   │   ├── exceptions.py    # custom errors + global handlers
│   │   └── utils.py         # small helpers (utcnow)
│   ├── models/              # DB tables (SQLAlchemy)   ~ Entity / schema.prisma
│   ├── schemas/             # request/response shapes  ~ DTOs
│   ├── services/            # business logic + queries ~ Services
│   └── routers/             # endpoints                ~ Controllers
├── alembic/                 # database migrations
├── alembic.ini
├── tests/
├── .env                     # your secrets (never commit)
├── .env.example
├── requirements.txt
└── README.md
```

Rule of thumb: routers handle HTTP only, services hold logic and DB queries,
models describe tables, schemas describe JSON.

---

# Commands

Creating the project from scratch (what each command does):

1. `mkdir taskapi && cd taskapi`
2. `python3 -m venv venv` - creates a standalone, isolated Python environment inside a new folder named `venv`.
3. `source venv/bin/activate` - turns on (activates) the virtual environment on Linux and macOS. Run this in every new terminal. Your prompt will show `(venv)`.
4. `pip install "fastapi[standard]"`
5. `pip freeze > requirements.txt` - saves all installed packages and their exact versions into `requirements.txt`.
6. `mkdir app`
7. `touch app/__init__.py app/main.py`

---

## Setup (using this project)

```bash
cd taskapi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Generate a secret and put it in `.env` as `JWT_SECRET`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Set `DATABASE_URL` in `.env`. In Supabase open your project, click Connect, and copy the
Session pooler string (port 5432). Add `+psycopg2` after `postgresql`:

```
DATABASE_URL=postgresql+psycopg2://postgres.YOURREF:YOURPASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
```

If your password has special characters, URL-encode them (`@` becomes `%40`).

## Create the database tables (Alembic)

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

## Start the server

```bash
uvicorn app.main:app --reload --port 8001
```

- `app.main:app` means file `app/main.py`, variable `app`
- `--reload` restarts on code changes (development only)
- If you get "Address already in use", pick another port or run `ss -ltnp | grep 8001`

Open:

- Swagger UI: http://localhost:8001/docs
- Health check: http://localhost:8001/health

## Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```

---

## Alembic (migrations)

Alembic keeps your database in sync with your Python models. When a model changes, it
compares models with the real database, writes a migration file, and you apply it.

```
Prisma                      Alembic
schema.prisma               app/models/*.py
prisma migrate dev          alembic revision --autogenerate -m "msg"  +  alembic upgrade head
prisma migrate deploy       alembic upgrade head
prisma/migrations           alembic/versions/
```

Daily workflow:

1. Edit or add a model in `app/models/`
2. `alembic revision --autogenerate -m "describe change"`
3. Read the new file in `alembic/versions/` and check it
4. `alembic upgrade head`

Useful commands:

```bash
alembic current         # which migration the DB is on
alembic history         # list migrations
alembic downgrade -1    # undo the last migration
```

If you add a new model, import it in `app/models/__init__.py` or Alembic won't see it.
Use the Supabase session pooler (port 5432) for migrations, not the transaction pooler (6543).

---

## How login works

1. `POST /auth/request-otp` with `{"email": "you@example.com"}`. A 6-digit code is created and emailed in a background task. Only a hash of the code is stored.
2. `POST /auth/verify-otp` with `{"email": "...", "code": "123456"}`. Returns a JWT. The user is created on first login.
3. Send `Authorization: Bearer <token>` on `/tasks` and `/auth/me`.

Rules: codes expire after 10 minutes, 5 wrong attempts burn the code, a code cannot be
reused, and a new code cannot be requested within 60 seconds.

In development leave `SMTP_HOST` empty in `.env`. The code is printed in the uvicorn
console as `[DEV] OTP for you@example.com: 123456`. For real emails fill in the
`SMTP_*` values (for Gmail use `smtp.gmail.com`, port 587, and an app password).

## Try it with curl

```bash
curl -X POST http://localhost:8001/auth/request-otp -H "Content-Type: application/json" -d '{"email":"you@example.com"}'
curl -X POST http://localhost:8001/auth/verify-otp -H "Content-Type: application/json" -d '{"email":"you@example.com","code":"123456"}'

TOKEN=paste_token_here
curl -X POST http://localhost:8001/tasks -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"title":"My first task"}'
curl "http://localhost:8001/tasks?limit=10&offset=0" -H "Authorization: Bearer $TOKEN"
curl -X PATCH http://localhost:8001/tasks/1 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"done":true}'
curl -X DELETE http://localhost:8001/tasks/1 -H "Authorization: Bearer $TOKEN"
```

In `/docs` click Authorize and paste the token to test everything from the browser.

## Endpoints

| Method | Path                | Auth | Description                       |
|--------|---------------------|------|-----------------------------------|
| GET    | /health             | no   | Health check                      |
| POST   | /auth/request-otp   | no   | Send a login code to an email     |
| POST   | /auth/verify-otp    | no   | Verify the code, get a JWT        |
| GET    | /auth/me            | yes  | Current user                      |
| GET    | /tasks              | yes  | List my tasks (done, limit, offset) |
| GET    | /tasks/{id}         | yes  | Get one of my tasks               |
| POST   | /tasks              | yes  | Create a task                     |
| PATCH  | /tasks/{id}         | yes  | Update a task                     |
| DELETE | /tasks/{id}         | yes  | Delete a task                     |

Errors always have the same shape:

```json
{"error": {"code": "not_found", "message": "Task not found"}}
```

---

# NestJS to FastAPI

| NestJS Concept | FastAPI Equivalent | How it works in FastAPI |
|---|---|---|
| Controller | APIRouter / Path Operations | Instead of a class with `@Controller()`, you define functions decorated with route methods (e.g. `@router.post("/users")`). |
| DTO (Data Transfer Object) | Pydantic Models | Instead of class-validator classes, you use Python classes inheriting from Pydantic's `BaseModel` for validation and serialization. |
| Guard | Dependencies (`Depends`) | There is no explicit "Guard" step. You write a function that handles auth/roles and pass it into your route (or router) with `Depends()`. |
| Middleware | Middleware | Same concept. Intercept requests globally using `@app.middleware("http")` or ASGI middleware classes. |
| Pipe | Dependencies or Pydantic validators | For transformation/validation use Pydantic fields (like `Field(gt=0)`) or a reusable `Depends` function. |
| Interceptors | Middleware / Dependencies | There is no dedicated Interceptor class. Use custom middleware or custom router classes to change requests/responses. |
| Providers / DI | `Depends()` | Nest uses constructor-based DI. FastAPI uses parameter-based DI via `Depends()`, with no global module registry. |
| Exception filter | `exception_handler` | See `app/core/exceptions.py`. |
| Config module | `pydantic-settings` | See `app/core/config.py`. |
| Entity / Prisma model | SQLAlchemy model | See `app/models/`. |
| Prisma migrate | Alembic | See the Alembic section above. |

## Code comparison

### 1. The DTO / Pydantic model

NestJS uses class-validator. FastAPI uses Pydantic out of the box to parse requests
and generate Swagger docs.

```python
from pydantic import BaseModel, EmailStr, Field

class CreateUserDTO(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
```

### 2. The Guard + Controller / Router

In NestJS you would use `@UseGuards(AuthGuard)`. In FastAPI you inject the guard
function into the route parameters with `Depends()`.

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["users"])

# This function acts like a NestJS Guard
def get_current_active_user(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

# This is the "Controller" route handler
@router.post("/", response_model=UserResponse)
def create_user(
    body: CreateUserDTO,                                   # validated against the DTO
    current_user: User = Depends(get_current_active_user)  # like @UseGuards()
):
    # business logic / service call here
    return {"message": "User created successfully"}
```

In this project the real guard is `get_current_user` in `app/deps.py`, and a whole
router is protected in one line:

```python
router = APIRouter(prefix="/tasks", dependencies=[Depends(get_current_user)])
```

### 3. Middleware

Global request/response interception works very similarly to Node.

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)   # let the request proceed to the router
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

## try / except in FastAPI

You rarely need it in routes. Raise your own errors (`NotFoundError`, `ConflictError`, ...)
from services and the global handler in `app/core/exceptions.py` turns them into JSON.
Use `try/except` only for specific expected failures, for example `IntegrityError` on a
duplicate row (remember `db.rollback()`) or an external HTTP/SMTP call.

## Notes

- Never commit `.env`.
- Tables created through the direct DB connection have no Row Level Security. That is fine
  because only this backend talks to the database. Enable RLS if you ever expose the
  Supabase REST API directly.
