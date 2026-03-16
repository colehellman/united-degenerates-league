"""Shared rate limiter instance.

All route-level rate limiting uses this single Limiter instance so that
app.state.limiter stays in sync and rate limits can be disabled globally
in test environments.

In test mode, .limit() returns a true identity decorator so that
coverage.py can trace the original function body (slowapi's wrapper
creates an opaque frame that coverage cannot see through).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

_is_test = settings.ENVIRONMENT in ("test",)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    enabled=not _is_test,
)

if _is_test:
    # Replace .limit() with an identity decorator so coverage can see
    # through to the actual endpoint function body.
    _original_limit = limiter.limit

    def _noop_limit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    limiter.limit = _noop_limit
