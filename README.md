# persysta-platform-fastapi-utils

Shared utilities for **Persysta** + **Vinon** FastAPI backends. Companion to
[`persysta-platform-auth-fastapi`](https://github.com/persysta-app/auth-fastapi)
(JWT auth) — that lib handles authentication; this one handles everything
else generic.

## Modules

| Module | What it does | Optional dep |
|---|---|---|
| `errors` | `err(code, **kwargs) -> dict` for translatable HTTPException details | — |
| `mixins` | `TimestampMixin`, `SoftDeleteMixin` for SQLAlchemy 2.x models | — |
| `sentry` | `init_sentry(...)` no-op when DSN empty | `sentry-sdk` (extra: `[sentry]`) |
| `rate_limit` | `build_limiter(...)` slowapi instance | `slowapi` (extra: `[rate-limit]`) |
| `email` | `send_email(...)` with SMTP STARTTLS + SendGrid HTTP API fallback + BackgroundTasks support | — |

## Install

```bash
pip install "persysta-platform-fastapi-utils @ https://github.com/persysta-app/fastapi-utils/archive/refs/tags/v0.1.0.tar.gz"
```

For Sentry/rate-limit features:

```bash
pip install "persysta-platform-fastapi-utils[sentry,rate-limit] @ ..."
```

## Usage

### errors

```python
from fastapi import HTTPException
from persysta_utils import err

raise HTTPException(status_code=409, detail=err("invoice_paid", invoice_id=42))
# → {"detail": {"code": "invoice_paid", "invoice_id": 42}}
```

### mixins

```python
from sqlalchemy.orm import Mapped, mapped_column
from persysta_utils import TimestampMixin, SoftDeleteMixin

class Product(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    # created_at, updated_at, deleted_at já vem dos mixins
```

### sentry

```python
from persysta_utils import init_sentry

init_sentry(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.05,
    release="myapp@1.2.3",
)
# noop se DSN vazio (dev mode)
```

### rate_limit

```python
from persysta_utils import build_limiter

limiter = build_limiter()
# Add a request handler (router level or app level):
# app.state.limiter = limiter
# app.add_middleware(SlowAPIMiddleware)

@router.post("/login")
@limiter.limit("20/minute")
def login(...): ...
```

### email

```python
from persysta_utils.email import send_email, SMTPConfig

cfg = SMTPConfig(
    host="smtp.sendgrid.net",   # or "sendgrid-api" for HTTP API mode
    port=587,
    user="apikey",
    password=sendgrid_api_key,
    tls=True,
    from_addr="My App <noreply@example.com>",
)

result = send_email(
    to="user@example.com",
    subject="Welcome",
    html_body="<p>Hi!</p>",
    text_body="Hi!",
    cfg=cfg,
)
# result.status: "sent" | "dev_logged" | "failed"
# result.error_message: str | None

# Async (FastAPI BackgroundTasks):
send_email(..., background_tasks=bg_tasks)
# returns immediately; SMTP runs after response
```

## Versioning

Semver. Breaking changes bump minor pre-1.0 (v0.X), major post-1.0.

## Status

- **v0.1.0** (2026-05-08): initial release with all 5 modules.
