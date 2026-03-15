"""Shared rate limiter instance.

All route-level rate limiting uses this single Limiter instance so that
app.state.limiter stays in sync and rate limits can be disabled globally
in test environments.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    enabled=settings.ENVIRONMENT not in ("test",),
)
