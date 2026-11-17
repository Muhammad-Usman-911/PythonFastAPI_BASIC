# FastAPI Starter: auth + email, ready to clone

A small, production-style **FastAPI** starter for new projects. It ships with exactly two things:
**authentication** and **email**. Everything else (your features) you add on top, using the same patterns.
It also doubles as a **guide for Node.js (Express / NestJS) developers moving to Python + FastAPI**.

![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![FastAPI](https://img.shields.io/badge/FastAPI-0.163-009688) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2-D71F00) ![Postgres](https://img.shields.io/badge/PostgreSQL%20%7C%20SQLite-ready-336791) ![Tests](https://img.shields.io/badge/tests-35%20passing-brightgreen) ![License](https://img.shields.io/badge/License-MIT-green)

**What you get**

- **Auth:** register with email + password, email verification by 6-digit code, password login,
  passwordless login (email code), access + refresh JWTs, forgot / reset password, change password,
  `/users/me`, role guard (`require_role("admin")`).
- **Email:** HTML templates, plain-text fallback, sent in the background. Three backends:
  `console` (prints in the terminal, zero setup), `smtp` (Gmail, Mailpit, SendGrid, SES, ...), `memory` (tests).
- **One response format** for every endpoint, success or error (see [Central responses and errors](#5-central-responses-and-errors)).
- SQLAlchemy 2 + Alembic migrations, SQLite by default, Postgres with one env var.
- Request id + timing middleware, CORS, structured error logging.
- Docker Compose (API + Postgres + Mailpit inbox), GitHub Actions CI, 35 tests (96% coverage).

---

## Contents

1. [Quick start (2 minutes)](#1-quick-start-2-minutes)
2. [Start a new project from this template](#2-start-a-new-project-from-this-template)
3. [Project structure](#3-project-structure)
4. [How a request works](#4-how-a-request-works)
5. [Central responses and errors](#5-central-responses-and-errors)
6. [Auth: how it works](#6-auth-how-it-works)
7. [Email: how it works](#7-email-how-it-works)
8. [Database and migrations (Alembic)](#8-database-and-migrations-alembic)
9. [Add a new feature (step by step)](#9-add-a-new-feature-step-by-step)
10. [Node.js → FastAPI guide](#10-nodejs--fastapi-guide)
11. [Tests, lint and CI](#11-tests-lint-and-ci)
12. [Deploy checklist](#12-deploy-checklist)
13. [Troubleshooting](#13-troubleshooting)

---

## Screenshots

| Swagger UI at `/docs` | Login: the success envelope |
|---|---|
| ![Swagger](docs/screenshots/01-swagger.png) | ![Login success](docs/screenshots/02-login-success.png) |

| Validation error: the error envelope | Verification email (Mailpit inbox) | Password reset email |
|---|---|---|
| ![Validation error](docs/screenshots/03-validation-error.png) | ![Verify email](docs/screenshots/04-email-verify.png) | ![Reset email](docs/screenshots/05-email-reset.png) |

---

## 1. Quick start (2 minutes)

You need **Python 3.12+** (check: `python3 --version`).

```bash
git clone git@github.com:Muhammad-Usman-911/PythonFastAPI_BASIC.git my-api
cd my-api

python3 -m venv .venv               # create an isolated environment (like a local node_modules)
source .venv/bin/activate           # turn it on (Windows: .venv\Scripts\activate). Do this in every new terminal.
pip install -r requirements-dev.txt # install packages (like `npm install`)

cp .env.example .env                # then set JWT_SECRET (see below)
alembic upgrade head                # create the tables (like `prisma migrate deploy`)
uvicorn app.main:app --reload       # start the dev server (like `nodemon`)
```

Generate a secret and paste it into `.env` as `JWT_SECRET`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Open **http://localhost:8000/docs** and try it:

1. `POST /api/v1/auth/register` with an email and a password like `Passw0rd!`
2. Look at the **uvicorn terminal**: the email (with the 6-digit code) is printed there
   (`EMAIL_BACKEND=console`)
3. `POST /api/v1/auth/verify-email` with the email and code. You get `access_token` + `refresh_token`
4. Click **Authorize**, paste the `access_token`, then call `GET /api/v1/users/me`

### Option B: everything in Docker (Postgres + a real inbox)

```bash
docker compose up --build
```

- API: http://localhost:8000/docs
- **Mailpit inbox: http://localhost:8025**: every email the API sends shows up here
- Postgres on `localhost:5432` (user / password / db: `app`)

Ports busy? Set `API_PORT`, `DB_PORT`, `MAILPIT_SMTP_PORT`, `MAILPIT_UI_PORT` in `.env`.
Stop with `docker compose down` (`-v` also deletes the database).

**Common mix:** run Postgres and Mailpit in Docker, and the API on your machine (fast reload):

```bash
docker compose up -d db mailpit
# in .env:
#   DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app
#   EMAIL_BACKEND=smtp  SMTP_HOST=localhost  SMTP_PORT=1025  SMTP_STARTTLS=false
alembic upgrade head
uvicorn app.main:app --reload
```

### The setup commands explained (if Python is new to you)

| Command | What it does | Node equivalent |
|---|---|---|
| `python3 -m venv .venv` | Creates an isolated Python + packages folder for this project | `node_modules/` (but it also holds the interpreter) |
| `source .venv/bin/activate` | Uses that environment in this terminal; your prompt shows `(.venv)` | nothing: npm uses `node_modules` automatically |
| `pip install -r requirements.txt` | Installs the pinned packages | `npm ci` |
| `pip install fastapi` then `pip freeze > requirements.txt` | Add a package and save exact versions | `npm install fastapi --save` |
| `uvicorn app.main:app --reload` | Starts the server; `app.main:app` = file `app/main.py`, variable `app` | `nodemon src/index.js` |
| `deactivate` | Leave the environment | — |

---

## 2. Start a new project from this template

```bash
git clone git@github.com:Muhammad-Usman-911/PythonFastAPI_BASIC.git my-new-api
cd my-new-api
rm -rf .git && git init -b main      # start a fresh history
```

Then:

1. Set `APP_NAME`, `EMAIL_FROM_NAME`, `FRONTEND_URL`, `CORS_ORIGINS` in `.env` (and `.env.example`).
2. Pick a database: keep SQLite, or set `DATABASE_URL` to Postgres / Supabase.
3. Pick an email setup: `console` for now; `smtp` with Mailpit, Gmail or a provider later.
4. Change the email colours / footer in `app/templates/email/base.html`.
5. Add your first feature with the [step-by-step recipe](#9-add-a-new-feature-step-by-step).
6. Don't need passwordless login, or password login? Delete its two routes in `app/routers/auth.py`
   and its functions in `app/services/auth_service.py`; the tests tell you what else used them.

---

## 3. Project structure

```
.
├── app/
│   ├── main.py               # creates the app: middleware, error handlers, routers, /health
│   ├── deps.py               # dependencies: get_db, CurrentUser, require_role, pagination
│   ├── core/                 # framework plumbing, rarely changes
│   │   ├── config.py         # all settings from .env (pydantic-settings)
│   │   ├── database.py       # engine, SessionLocal, Base for models
│   │   ├── responses.py      # ApiResponse / ErrorResponse / Page + ok() helper   ← response format
│   │   ├── exceptions.py     # AppError classes + the 4 global handlers           ← error format
│   │   ├── middleware.py     # CORS, request id, timing, request log
│   │   ├── security.py       # bcrypt, JWT create/decode, OTP hashing
│   │   └── utils.py          # utcnow(), as_utc()
│   ├── models/               # database tables (SQLAlchemy)          ~ Prisma models / TypeORM entities
│   │   ├── user.py
│   │   └── otp.py            # one-time codes + their purpose (login / verify_email / reset_password)
│   ├── schemas/              # request + response shapes (Pydantic)   ~ DTOs / zod schemas
│   │   ├── auth.py
│   │   └── user.py
│   ├── services/             # business logic + DB queries           ~ NestJS services
│   │   ├── auth_service.py
│   │   ├── otp_service.py
│   │   ├── user_service.py
│   │   └── email_service.py  # templates + send_email() + one function per email
│   ├── routers/              # HTTP endpoints only                    ~ Express routers / Nest controllers
│   │   ├── auth.py
│   │   └── users.py
│   └── templates/email/      # base.html (layout), code.html, notice.html
├── alembic/                  # migrations (versions/ holds one file per schema change)
├── tests/                    # pytest: conftest.py (fixtures), test_auth/users/core.py
├── docs/screenshots/
├── Dockerfile · docker-compose.yml · .github/workflows/ci.yml
├── requirements.txt · requirements-dev.txt · pyproject.toml (ruff, pytest config)
└── .env.example
```

**The rule:** `routers` handle HTTP only → `services` hold the rules and the queries → `models` are the tables,
`schemas` are the JSON. A router never runs a query; a service never builds an HTTP response.

---

## 4. How a request works

```mermaid
flowchart LR
    C[Client] -->|HTTP| MW["Middleware<br/>CORS · request id · timing<br/>core/middleware.py"]
    MW --> RT["Router<br/>routers/*.py"]
    RT -->|"validates body/query"| SC["Schemas<br/>schemas/*.py"]
    SC -. invalid .-> EH
    RT -->|"Depends()"| DP["Dependencies<br/>deps.py<br/>get_db · CurrentUser · require_role"]
    RT --> SV["Service<br/>services/*.py<br/>business rules"]
    SV --> DB[("Database<br/>SQLite / Postgres")]
    SV -. "raise AppError" .-> EH["Exception handlers<br/>core/exceptions.py"]
    SV -->|returns data| RT
    RT -->|"ok(data) + response_model"| OUT["{success: true, data}"]
    EH --> ERR["{success: false, error}"]
    RT -. "BackgroundTasks" .-> EM["email_service<br/>after the response"]
```

Step by step for `POST /api/v1/auth/register`:

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant M as Middleware
    participant R as routers/auth.py
    participant S as auth_service
    participant DB as Database
    participant E as email_service
    C->>M: POST /api/v1/auth/register {email, password}
    M->>M: request_id = X-Request-ID or new id
    M->>R: call_next(request)
    R->>R: validate body as RegisterIn (bad → 422 envelope)
    R->>S: register(db, data)
    S->>DB: email taken? (→ 409 email_taken)
    S->>DB: INSERT user (bcrypt hash), INSERT otp (HMAC of code)
    S-->>R: (user, code)
    R->>R: background.add_task(send_verification_code)
    R-->>C: 201 {success: true, message, data: UserOut}
    R->>E: after the response: render template, send via backend
```

Things worth knowing:

- **Validation is automatic.** The route's parameter `data: RegisterIn` makes FastAPI parse and validate the
  JSON. If it fails, your function never runs.
- **`Depends()` is dependency injection.** `db: DbSession` gives a DB session that is closed after the request;
  `user: CurrentUser` runs the JWT check and gives you the `User`. Same idea as a Nest guard/provider.
- **`response_model` is a filter.** Only fields declared in the schema are sent. `UserOut` has no
  `hashed_password`, so it can never leak, even though the route returns the full database object.
- **Background tasks** run after the response is sent, in the same process. Fine for emails. For heavy or
  must-not-lose jobs use a queue (Celery, RQ, arq), like BullMQ in Node.

---

## 5. Central responses and errors

Every endpoint returns the same envelope, so a frontend handles all responses in one place.

**Success**

```json
{
  "success": true,
  "message": "Logged in",
  "data": { "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "expires_in": 1800 }
}
```

**Error** (any error: yours, validation, unknown route, crash)

```json
{
  "success": false,
  "message": "Incorrect email or password",
  "error": { "code": "invalid_credentials", "details": null, "request_id": "4f1c2a9b7e01" }
}
```

- `message`: human readable, safe to show in a toast
- `error.code`: stable machine-readable string: branch on this in the frontend, not on the message
- `error.details`: extra data, e.g. the invalid fields for validation errors, `retry_after_seconds` for 429
- `error.request_id`: also in the `X-Request-ID` header and in the server log line, to find the request in logs

**Validation error** (422) lists every bad field:

```json
{
  "success": false,
  "message": "Validation failed",
  "error": {
    "code": "validation_error",
    "details": [
      { "field": "body.email", "message": "value is not a valid email address: ...", "type": "value_error" },
      { "field": "body.password", "message": "Password must be at least 8 characters", "type": "value_error" }
    ],
    "request_id": "614f3268fab3"
  }
}
```

### How it's wired

| Piece | File | Job |
|---|---|---|
| `ApiResponse[T]`, `Page[T]`, `ErrorResponse` | `app/core/responses.py` | The shapes (also shown in Swagger) |
| `ok(data, message)` | `app/core/responses.py` | Build a success envelope in a route |
| `AppError` + subclasses | `app/core/exceptions.py` | Raise these anywhere |
| 4 handlers in `register_exception_handlers()` | `app/core/exceptions.py` | Turn **every** error into the envelope |
| `ERROR_RESPONSES` | `app/core/responses.py` | Documents error responses on a router in Swagger |

The four handlers:

| Handler catches | Example | Status / code |
|---|---|---|
| `AppError` (yours) | `raise NotFoundError("User not found")` | its own status / code |
| `RequestValidationError` | bad JSON body, `?limit=500` | 422 `validation_error` + field list |
| `StarletteHTTPException` | unknown URL, wrong method, `raise HTTPException(...)` | 404 `not_found`, 405 `method_not_allowed`, ... |
| `Exception` (anything else) | a bug, DB down | 500 `internal_error`; full traceback logged, nothing leaked |

### Using it

```python
from app.core.exceptions import ConflictError, NotFoundError
from app.core.responses import ApiResponse, ok

@router.get("/projects/{project_id}", response_model=ApiResponse[ProjectOut])
def get_project(project_id: int, db: DbSession, user: CurrentUser):
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise NotFoundError("Project not found")            # → 404 {"success": false, ...}
    return ok(project)                                      # → 200 {"success": true, "data": {...}}

# custom code + details:
raise ConflictError("Slug already used", code="slug_taken", details={"slug": slug})
```

Available errors: `BadRequestError` 400 · `UnauthorizedError` 401 · `ForbiddenError` 403 · `NotFoundError` 404 ·
`ConflictError` 409 · `TooManyRequestsError` 429. Need another? Subclass `AppError`:

```python
class PaymentRequiredError(AppError):
    status_code = 402
    code = "payment_required"
```

**No try/except in routes.** Raise from services and let the handlers answer. Use `try/except` only for a
specific failure you can handle, e.g. `IntegrityError` on a duplicate row (call `db.rollback()`), or an
external API call you want to retry.

### Error codes this starter uses

| Code | Status | When |
|---|---|---|
| `validation_error` | 422 | Body / query / path params invalid |
| `not_authenticated` | 401 | No `Authorization: Bearer` header |
| `invalid_token` / `token_expired` | 401 | Bad, wrong-type or expired JWT |
| `invalid_credentials` | 401 | Wrong email or password (same message for both) |
| `email_not_verified` | 403 | Password login before verifying (`REQUIRE_EMAIL_VERIFICATION=true`) |
| `account_disabled` | 403 | `users.is_active = false` |
| `insufficient_role` | 403 | `require_role(...)` failed |
| `email_taken` | 409 | Register with an existing email |
| `invalid_code` | 400 | Wrong, expired, used or burned one-time code |
| `otp_cooldown` | 429 | New code asked within `OTP_RESEND_SECONDS` |
| `wrong_password` | 400 | Change password with a wrong current password |
| `not_found` / `method_not_allowed` | 404 / 405 | Unknown route / wrong HTTP method |
| `internal_error` | 500 | Unexpected exception (see the server log by `request_id`) |

### Frontend helper (TypeScript)

```ts
type ApiOk<T> = { success: true; message: string | null; data: T };
type ApiErr = { success: false; message: string; error: { code: string; details: unknown; request_id: string | null } };

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(token() && { Authorization: `Bearer ${token()}` }), ...init.headers },
  });
  const body = (await res.json()) as ApiOk<T> | ApiErr;
  if (!body.success) throw Object.assign(new Error(body.message), body.error); // err.code, err.details
  return body.data;
}
```

---

## 6. Auth: how it works

### Endpoints (`/api/v1`)

| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `/auth/register` | — | Create account (email, password, full_name). Emails a verification code |
| POST | `/auth/verify-email` | — | Email + code → marks verified, returns tokens, sends a welcome email |
| POST | `/auth/resend-verification` | — | New verification code (same answer for unknown emails) |
| POST | `/auth/login` | — | Email + password → tokens |
| POST | `/auth/login/code` | — | Passwordless step 1: email a login code |
| POST | `/auth/login/code/verify` | — | Passwordless step 2: code → tokens (creates the account on first login) |
| POST | `/auth/refresh` | — | Refresh token → new token pair |
| POST | `/auth/forgot-password` | — | Email a reset code (same answer for unknown emails) |
| POST | `/auth/reset-password` | — | Email + code + new password |
| GET | `/users/me` | Bearer | Current user |
| PATCH | `/users/me` | Bearer | Update profile (`full_name`) |
| POST | `/users/me/change-password` | Bearer | Change (or set a first) password; emails a notice |
| GET | `/users` | Bearer + admin | Example of a role-protected, paginated list |
| GET | `/health` | — | App + database check |

### The flows

```mermaid
sequenceDiagram
    participant U as User / Frontend
    participant A as API
    participant M as Inbox
    Note over U,M: Sign up
    U->>A: POST /auth/register {email, password}
    A-->>M: "Confirm your email" (code)
    U->>A: POST /auth/verify-email {email, code}
    A-->>U: access_token + refresh_token
    Note over U,M: Every request
    U->>A: GET /users/me  (Authorization: Bearer access_token)
    Note over U,M: Access token expired (401 token_expired)
    U->>A: POST /auth/refresh {refresh_token}
    A-->>U: new token pair
    Note over U,M: Forgot password
    U->>A: POST /auth/forgot-password {email}
    A-->>M: "Reset your password" (code)
    U->>A: POST /auth/reset-password {email, code, new_password}
```

### Tokens

- **Access token**: short (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30). Sent on every request.
- **Refresh token**: long (`REFRESH_TOKEN_EXPIRE_DAYS`, default 7). Only for `POST /auth/refresh`.
- Both are HS256 JWTs with `sub` (user id), `type` (`access` / `refresh`), `iat`, `exp`.
  The `type` claim means a refresh token is refused as an access token and vice versa.
- Frontend pattern: on a 401 with `code === "token_expired"`, call `/auth/refresh` once, retry the request.

### One-time codes (OTP)

- 6 digits from `secrets` (cryptographically secure). Only an **HMAC** of the code is stored.
- Each code has a **purpose** (`login`, `verify_email`, `reset_password`): a login code can't reset a password.
- Expires after `OTP_EXPIRE_MINUTES` (10), used once, burned after `OTP_MAX_ATTEMPTS` (5) wrong tries,
  new code allowed after `OTP_RESEND_SECONDS` (60). A new code cancels older ones.

### Passwords

- Hashed with **bcrypt**. Rules in `check_password_strength()` (`app/schemas/auth.py`):
  at least `PASSWORD_MIN_LENGTH` (8) characters, a letter and a number, max 72 bytes (bcrypt limit).
- Login gives the same error for "no such email" and "wrong password", so attackers can't discover accounts.
  `forgot-password`, `resend-verification` and `login/code` answer the same way for unknown emails too.

### Protect your own routes

```python
from app.deps import CurrentUser, require_role

@router.get("/invoices")
def my_invoices(user: CurrentUser, db: DbSession): ...           # any logged-in user

@router.delete("/invoices/{id}")
def delete_invoice(id: int, admin: Annotated[User, Depends(require_role("admin"))]): ...

# a whole router:
router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))])
```

Make someone admin (no endpoint on purpose): `UPDATE users SET role = 'admin' WHERE email = 'you@example.com';`

---

## 7. Email: how it works

`app/services/email_service.py` has one `send_email(to, subject, html, text)` and one small function per email
(`send_verification_code`, `send_login_code`, `send_password_reset_code`, `send_welcome`, `send_password_changed`).
Routers call them with `background.add_task(...)`, so the client never waits for SMTP; failures are logged.

| `EMAIL_BACKEND` | What happens | Use it for |
|---|---|---|
| `console` (default) | Email printed in the uvicorn terminal | Local dev, zero setup |
| `smtp` | Really sent, HTML + plain text | Mailpit (local inbox), Gmail, any provider's SMTP |
| `memory` | Appended to `email_service.outbox` | Tests (they read codes from it) |

**Templates** live in `app/templates/email/`: `base.html` is the layout (header colour, footer),
`code.html` shows a big code, `notice.html` is a message with a button. They use Python's built-in
`string.Template` (`${name}` placeholders); values are HTML-escaped. The plain-text part is generated from the HTML.

**Add a new email:**

```python
# app/services/email_service.py
def send_invite(to: str, inviter: str, link: str) -> None:
    subject = f"{inviter} invited you to {settings.APP_NAME}"
    body = render("notice.html", subject, title="You're invited", body=f"{inviter} invited you.",
                  link=link, link_text="Accept invite")
    send_email(to, subject, body)

# in a router:
background.add_task(email_service.send_invite, data.email, user.full_name, link)
```

**SMTP settings** (in `.env`):

| Provider | Settings |
|---|---|
| Mailpit (Docker) | `SMTP_HOST=localhost SMTP_PORT=1025 SMTP_STARTTLS=false`, inbox at http://localhost:8025 |
| Gmail | `SMTP_HOST=smtp.gmail.com SMTP_PORT=587 SMTP_USER=you@gmail.com SMTP_PASSWORD=<App Password> EMAIL_FROM=you@gmail.com` (needs 2FA + an [App Password](https://myaccount.google.com/apppasswords)) |
| SendGrid | `SMTP_HOST=smtp.sendgrid.net SMTP_PORT=587 SMTP_USER=apikey SMTP_PASSWORD=<API key>` |
| Port 465 providers | `SMTP_PORT=465 SMTP_SSL=true SMTP_STARTTLS=false` |

In production send from a domain you own with SPF/DKIM set up, or emails land in spam.

---

## 8. Database and migrations (Alembic)

- **SQLite** (`sqlite:///./app.db`) is the default: nothing to install.
- **Postgres**: `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db` (driver: psycopg 3).
- **Supabase**: Connect → *Session pooler* (port 5432), then add `+psycopg` after `postgresql`.
  URL-encode special characters in the password (`@` → `%40`). Use the session pooler (5432) for migrations,
  not the transaction pooler (6543).

Alembic keeps the database in sync with your models: it compares models with the real database,
writes a migration file, and you apply it.

```
Prisma                      Alembic
schema.prisma               app/models/*.py
prisma migrate dev          alembic revision --autogenerate -m "msg"  +  alembic upgrade head
prisma migrate deploy       alembic upgrade head
prisma/migrations           alembic/versions/
```

Daily workflow:

1. Edit or add a model in `app/models/` (new model? import it in `app/models/__init__.py`)
2. `alembic revision --autogenerate -m "add projects table"`
3. **Read** the new file in `alembic/versions/` and fix it if needed (autogenerate misses renames)
4. `alembic upgrade head`

```bash
alembic current         # which migration the DB is on
alembic history         # list migrations
alembic downgrade -1    # undo the last migration
alembic check           # do the models and the DB match? (CI runs this)
```

The Docker image runs `alembic upgrade head` on start, so deploys migrate automatically.

---

## 9. Add a new feature (step by step)

Example: a `Project` that belongs to a user.

**1. Model**: `app/models/project.py`, then import it in `app/models/__init__.py`

```python
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

**2. Migration**: `alembic revision --autogenerate -m "projects"` → read it → `alembic upgrade head`

**3. Schemas**: `app/schemas/project.py`

```python
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
```

**4. Service**: `app/services/project_service.py` (rules + queries, raises `AppError`s)

```python
def create(db: Session, owner: User, data: ProjectCreate) -> Project:
    project = Project(owner_id=owner.id, name=data.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def list_for(db: Session, owner: User, limit: int, offset: int) -> tuple[list[Project], int]:
    query = select(Project).where(Project.owner_id == owner.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Project.id.desc()).limit(limit).offset(offset)).all()
    return list(items), total
```

**5. Router**: `app/routers/projects.py`

```python
router = APIRouter(prefix="/projects", tags=["projects"], responses=ERROR_RESPONSES)

@router.post("", response_model=ApiResponse[ProjectOut], status_code=201)
def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession):
    return ok(project_service.create(db, user, data), "Project created")

@router.get("", response_model=ApiResponse[Page[ProjectOut]])
def list_projects(user: CurrentUser, db: DbSession, page: PaginationDep):
    items, total = project_service.list_for(db, user, page.limit, page.offset)
    return ok({"items": items, "total": total, "limit": page.limit, "offset": page.offset})
```

**6. Register it** in `app/main.py`: `app.include_router(projects.router, prefix=settings.API_PREFIX)`

**7. Test it**: `tests/test_projects.py`, reusing the helpers in `tests/conftest.py`

```python
def test_create_and_list(client):
    h = auth_header(verified_user(client))
    assert client.post(f"{API}/projects", json={"name": "Site"}, headers=h).status_code == 201
    assert client.get(f"{API}/projects", headers=h).json()["data"]["total"] == 1
```

---

## 10. Node.js → FastAPI guide

### Concepts side by side

| Node (Express / NestJS) | FastAPI / Python | In this repo |
|---|---|---|
| `package.json` dependencies | `requirements.txt` (or `pyproject.toml`) | `requirements*.txt` |
| `node_modules/` | virtual env `.venv/` | `python -m venv .venv` |
| `npm ci` / `npm install x` | `pip install -r requirements.txt` / `pip install x` | — |
| `nodemon index.js` | `uvicorn app.main:app --reload` | — |
| `express()` / `NestFactory.create()` | `FastAPI()` | `app/main.py` |
| `express.Router()` / `@Controller()` | `APIRouter()` | `app/routers/` |
| `req.body` + zod / class-validator DTO | typed parameter with a Pydantic `BaseModel` | `app/schemas/` |
| `req.params.id`, `req.query.limit` | function params: `id: int`, `limit: int = Query(20, le=100)` | `deps.pagination_params` |
| `res.status(201).json(x)` | `status_code=201` on the decorator + `return x` | routers |
| auth middleware setting `req.user` / `@UseGuards(JwtAuthGuard)` | `user: CurrentUser` (= `Depends(get_current_user)`) | `app/deps.py` |
| `RolesGuard` + `@Roles('admin')` | `Depends(require_role("admin"))` | `app/deps.py` |
| Nest providers / constructor DI | `Depends()` in function parameters | `DbSession`, `CurrentUser` |
| `app.use((req, res, next) => ...)` | `@app.middleware("http")` with `await call_next(request)` | `app/core/middleware.py` |
| `cors()` | `CORSMiddleware` | `app/core/middleware.py` |
| error middleware `(err, req, res, next)` / exception filter | `@app.exception_handler(...)` | `app/core/exceptions.py` |
| interceptor that wraps responses | `ok()` + `response_model=ApiResponse[T]` | `app/core/responses.py` |
| `dotenv` + config module | `pydantic-settings` `BaseSettings` | `app/core/config.py` |
| Prisma / TypeORM | SQLAlchemy 2 | `app/models/` |
| `prisma migrate` | Alembic | `alembic/` |
| `bcrypt`, `jsonwebtoken` | `bcrypt`, `PyJWT` | `app/core/security.py` |
| `nodemailer` + handlebars | `smtplib` + `string.Template` | `app/services/email_service.py` |
| `setImmediate` / fire-and-forget after response | `BackgroundTasks` | `app/routers/auth.py` |
| Swagger via `@nestjs/swagger` decorators | automatic at `/docs` and `/redoc` | — |
| Jest + supertest | pytest + `TestClient` | `tests/` |
| eslint + prettier | ruff (`ruff check`, `ruff format`) | `pyproject.toml` |

### The same endpoint in Express and FastAPI

```js
// Express
router.post("/projects", auth, async (req, res, next) => {
  const parsed = ProjectCreate.safeParse(req.body);           // zod
  if (!parsed.success) return res.status(422).json(...);
  try {
    const project = await projectService.create(req.user, parsed.data);
    res.status(201).json({ success: true, data: project });
  } catch (e) { next(e); }
});
```

```python
# FastAPI
@router.post("/projects", response_model=ApiResponse[ProjectOut], status_code=201)
def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession):
    return ok(project_service.create(db, user, data))
```

Validation, auth, the DB session, the status code, error forwarding and the Swagger docs all come from the
**type hints** and the decorator.

### `def` or `async def`? (the most important difference from Node)

Node has one thread and everything I/O is async. FastAPI supports both styles:

- **`def` route** (used in this starter): FastAPI runs it in a **thread pool**, so blocking code
  (SQLAlchemy sync session, `smtplib`, `bcrypt`) is fine and doesn't freeze the server.
- **`async def` route**: runs on the event loop like Node. Inside it you must only `await` async libraries
  (`httpx.AsyncClient`, async SQLAlchemy, `asyncpg`). **One blocking call in an `async def` blocks every request**,
  like a `while(true)` in Node.

Rule of thumb: sync libraries → `def`. All-async stack → `async def`. Don't mix blocking calls into `async def`.

### Python syntax a JS developer trips over

| JavaScript / TypeScript | Python |
|---|---|
| `const x: number \| null = null` | `x: int \| None = None` |
| `{ ...a, b: 1 }` | `{**a, "b": 1}` |
| `arr.map(x => x * 2)` | `[x * 2 for x in arr]` |
| `arr.filter(Boolean)` | `[x for x in arr if x]` |
| `` `Hello ${name}` `` | `f"Hello {name}"` |
| `a ?? b` / `a \|\| b` | `a if a is not None else b` / `a or b` |
| `obj?.prop` | `getattr(obj, "prop", None)` (no optional chaining) |
| `import { x } from "./y"` | `from app.y import x` (absolute imports from the project root) |
| `export` | everything at module level is importable; `_name` means "private by convention" |
| `try {} catch (e) {} finally {}` | `try: ... except SomeError as e: ... finally: ...` |
| `throw new Error("x")` | `raise ValueError("x")` |
| `class A extends B` | `class A(B):` |
| `interface User { id: number }` | `class User(BaseModel): id: int` (validated at runtime too) |
| `null` / `undefined` | `None` only |
| `===` | `==` (and `is` for `None`: `if x is None`) |
| indentation is style | **indentation is syntax** (4 spaces) |

---

## 11. Tests, lint and CI

```bash
pytest                                   # 35 tests, SQLite temp DB, emails captured in memory
pytest --cov --cov-report=term-missing   # coverage (~96%)
pytest tests/test_auth.py -k refresh     # one file / tests matching a name
ruff check . && ruff format .            # lint + format (like eslint --fix + prettier)
```

How the tests work (`tests/conftest.py`): env vars are set **before** the app is imported
(`EMAIL_BACKEND=memory`, a temp SQLite DB); every test starts with empty tables; helpers `register()`,
`verified_user()`, `auth_header()` and `last_code(email)` (reads the code from the captured email) keep tests short.
`test_core.py` also runs `alembic upgrade head` + `alembic check` to prove the migrations match the models.

**CI** (`.github/workflows/ci.yml`) on every push and pull request: ruff, pytest with an 85% coverage floor,
and a Postgres job that applies, checks, rolls back and re-applies the migrations.

---

## 12. Deploy checklist

- [ ] `ENVIRONMENT=production` (hides `/docs` and `/redoc`; remove that in `main.py` if your API is public)
- [ ] Long random `JWT_SECRET` (never reuse the dev one); real `DATABASE_URL` (Postgres)
- [ ] `CORS_ORIGINS` = your real frontend URL(s) only
- [ ] `EMAIL_BACKEND=smtp` with a real provider; SPF/DKIM on the sending domain
- [ ] Run behind HTTPS (Render, Railway, Fly.io, a VPS with Caddy/Nginx). The Dockerfile is ready:
      it migrates and starts uvicorn on port 8000 with `--proxy-headers`
- [ ] Health check path: `/health`
- [ ] More workers for more traffic: `uvicorn app.main:app --workers 4` (or gunicorn with uvicorn workers)
- [ ] Next steps you may want: rate limiting on login (e.g. `slowapi`), refresh-token revocation list,
      Sentry for errors, a job queue for heavy background work

---

## 13. Troubleshooting

| Problem | Fix |
|---|---|
| `JWT_SECRET Field required` / `at least 32 characters` | `cp .env.example .env` and set a long `JWT_SECRET` |
| `ModuleNotFoundError: No module named 'app'` | Run commands from the project root, with the venv activated |
| `command not found: uvicorn / alembic` | `source .venv/bin/activate` first |
| `no such table: users` | `alembic upgrade head` |
| Alembic doesn't see a new model | Import it in `app/models/__init__.py` |
| `Address already in use` | `uvicorn app.main:app --reload --port 8001` (or find it: `ss -ltnp \| grep 8000`) |
| No email arrives | With `console`, it's in the uvicorn terminal. With `smtp`, check the server log for `Failed to send email` |
| Gmail `Username and Password not accepted` | Use an App Password (needs 2FA), not your normal password |
| CORS error in the browser | Add the frontend origin (scheme + host + port) to `CORS_ORIGINS` |
| 500 `internal_error` | Find the `request_id` in the server log: the full traceback is there |

---

## License

MIT
