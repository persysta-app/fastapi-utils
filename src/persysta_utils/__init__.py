"""persysta-platform-fastapi-utils — shared utility lib.

Public API for Persysta + Vinon consumers.
"""
from .audit import AuditLogMixin, log_action
from .errors import err
from .health import build_health_router
from .mixins import SoftDeleteMixin, TimestampMixin
from .rate_limit import build_limiter
from .security_headers import add_security_headers_middleware
from .sentry import init_sentry

__version__ = "0.3.0"

__all__ = [
    # Errors
    "err",
    # DB mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    # Sentry
    "init_sentry",
    # Rate limit
    "build_limiter",
    # Security headers (v0.2)
    "add_security_headers_middleware",
    # Health (v0.2)
    "build_health_router",
    # Audit (v0.2)
    "AuditLogMixin",
    "log_action",
    # Email module exposed via `persysta_utils.email` (sub-package)
]
