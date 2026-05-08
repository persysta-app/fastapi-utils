"""persysta-platform-fastapi-utils — shared utility lib.

Public API for Persysta + Vinon consumers.
"""
from .errors import err
from .mixins import SoftDeleteMixin, TimestampMixin
from .rate_limit import build_limiter
from .sentry import init_sentry

__version__ = "0.1.0"

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
    # Email module exposed via `persysta_utils.email` (sub-package)
]
