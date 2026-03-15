"""Redis-backed token blacklist for refresh token revocation.

When a user logs out, changes their password, or deletes their account,
their refresh token's JTI (JWT ID) is added to a Redis set with a TTL
matching the token's remaining lifetime. On every refresh attempt, the
JTI is checked against this blacklist before issuing new tokens.

Falls back to an in-memory set when Redis is unavailable (development).
The in-memory set is process-local and does NOT survive restarts, so
production deployments MUST have Redis configured.
"""

import logging
from datetime import datetime
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory fallback for when Redis is unavailable
_memory_blacklist: set[str] = set()


def _get_redis():
    """Get a synchronous Redis client, or None if unavailable."""
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception:
        return None


def blacklist_token(jti: str, exp: Optional[int] = None) -> None:
    """Add a token's JTI to the blacklist.

    Args:
        jti: The JWT ID claim from the token.
        exp: The token's expiration timestamp (unix epoch). Used to set
             the Redis key TTL so entries auto-expire.
    """
    if not jti:
        return

    # Calculate TTL from expiration timestamp
    ttl = None
    if exp:
        ttl = max(int(exp - datetime.utcnow().timestamp()), 0)
        if ttl <= 0:
            return  # Token already expired, no need to blacklist

    client = _get_redis()
    if client:
        try:
            key = f"token_blacklist:{jti}"
            if ttl:
                client.setex(key, ttl, "1")
            else:
                # Default: expire after max refresh token lifetime
                client.setex(key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")
            client.close()
            return
        except Exception as e:
            logger.warning(f"Redis blacklist set failed, using memory fallback: {e}")
            if client:
                client.close()

    # Fallback: in-memory (development only — not shared across processes)
    _memory_blacklist.add(jti)


def is_token_blacklisted(jti: str) -> bool:
    """Check if a token's JTI is blacklisted."""
    if not jti:
        return False

    client = _get_redis()
    if client:
        try:
            result = client.exists(f"token_blacklist:{jti}")
            client.close()
            return bool(result)
        except Exception as e:
            logger.warning(f"Redis blacklist check failed, using memory fallback: {e}")
            if client:
                client.close()

    return jti in _memory_blacklist


def blacklist_all_user_tokens(user_id: str) -> None:
    """Blacklist all tokens for a user by storing a 'user revoked at' timestamp.

    Any refresh token issued before this timestamp will be rejected.
    Used for password changes and account deletion.
    """
    client = _get_redis()
    if client:
        try:
            key = f"user_tokens_revoked:{user_id}"
            now = int(datetime.utcnow().timestamp())
            client.setex(key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, str(now))
            client.close()
            return
        except Exception as e:
            logger.warning(f"Redis user revocation failed: {e}")
            if client:
                client.close()


def is_user_token_revoked(user_id: str, token_iat: Optional[int] = None) -> bool:
    """Check if a user's tokens were revoked after the given token was issued."""
    if not token_iat:
        return False

    client = _get_redis()
    if client:
        try:
            key = f"user_tokens_revoked:{user_id}"
            revoked_at = client.get(key)
            client.close()
            if revoked_at:
                return token_iat < int(revoked_at)
            return False
        except Exception as e:
            logger.warning(f"Redis user revocation check failed: {e}")
            if client:
                client.close()

    return False
