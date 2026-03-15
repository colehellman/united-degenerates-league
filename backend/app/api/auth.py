import uuid
import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, verify_token
from app.models.user import User, AccountStatus
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from app.services.token_blacklist import blacklist_token, is_token_blacklisted, is_user_token_revoked

logger = logging.getLogger(__name__)


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


router = APIRouter()

# Stricter rate limiter for auth endpoints (brute-force protection)
auth_limiter = Limiter(key_func=get_remote_address)

# Cookie configuration
_is_prod = settings.ENVIRONMENT == "production"
_cookie_kwargs = {
    "httponly": True,
    "secure": _is_prod,
    "samesite": "none" if _is_prod else "lax",
    "path": "/",
}


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly cookies for both tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_cookie_kwargs,
    )


def _clear_auth_cookies(response: Response):
    """Clear auth cookies on logout.

    Must pass the same samesite/secure attributes used at set-time — browsers
    match cookies by name + path + domain + samesite + secure.  Without these,
    the deletion Set-Cookie targets a *different* cookie and is silently ignored.
    """
    response.delete_cookie("access_token", **_cookie_kwargs)
    response.delete_cookie("refresh_token", **_cookie_kwargs)


def _check_account_lockout(user: User) -> None:
    """Raise 429 if user has exceeded failed login attempts."""
    if (
        user.failed_login_attempts
        and user.failed_login_attempts >= settings.AUTH_LOCKOUT_ATTEMPTS
        and user.locked_until
        and user.locked_until > datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed login attempts. Try again later.",
        )


async def _record_failed_login(db: AsyncSession, user: User) -> None:
    """Increment failed login counter and lock if threshold exceeded."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= settings.AUTH_LOCKOUT_ATTEMPTS:
        from datetime import timedelta
        user.locked_until = datetime.utcnow() + timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
        logger.warning(f"Account locked for user {user.id} after {user.failed_login_attempts} failed attempts")
    await db.commit()


async def _clear_failed_logins(db: AsyncSession, user: User) -> None:
    """Reset failed login counter on successful login."""
    if user.failed_login_attempts:
        user.failed_login_attempts = 0
        user.locked_until = None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@auth_limiter.limit(settings.AUTH_RATE_LIMIT)
async def register(
    request: Request,
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user"""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_username = result.scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        status=AccountStatus.ACTIVE,
    )

    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Race condition: another request registered the same email/username
        # between our check and commit. Return a generic message.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already taken",
        )
    await db.refresh(new_user)

    # Create tokens
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id), "jti": str(uuid.uuid4())})

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=TokenResponse)
@auth_limiter.limit(settings.AUTH_RATE_LIMIT)
async def login(
    request: Request,
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password"""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account lockout before verifying password
    _check_account_lockout(user)

    if not verify_password(credentials.password, user.hashed_password):
        await _record_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    # Clear failed login counter and update last login
    await _clear_failed_logins(db, user)
    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "jti": str(uuid.uuid4())})

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
@auth_limiter.limit(settings.AUTH_RATE_LIMIT)
async def refresh_tokens(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for new access + refresh tokens.

    Accepts refresh token from either:
    - Request body (JSON): {"refresh_token": "..."}
    - httpOnly cookie (automatic)
    """
    # Prefer body token, fall back to cookie
    token = body.refresh_token or refresh_token_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    payload = verify_token(token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Check if this specific token has been blacklisted (logout)
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    # Check if all user tokens were revoked (password change / account deletion)
    token_iat = payload.get("iat")
    if is_user_token_revoked(user_id, token_iat):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Blacklist the old refresh token (one-time use)
    if jti:
        blacklist_token(jti, payload.get("exp"))

    # Issue new token pair (rotate refresh token for security)
    new_jti = str(uuid.uuid4())
    new_access = create_access_token(data={"sub": str(user.id)})
    new_refresh = create_refresh_token(data={"sub": str(user.id), "jti": new_jti})

    _set_auth_cookies(response, new_access, new_refresh)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    body: RefreshRequest = RefreshRequest(),
):
    """Clear auth cookies and blacklist the refresh token server-side."""
    # Blacklist the refresh token so it can't be reused
    token = body.refresh_token or refresh_token_cookie
    if token:
        payload = verify_token(token, token_type="refresh")
        if payload:
            jti = payload.get("jti")
            if jti:
                blacklist_token(jti, payload.get("exp"))

    _clear_auth_cookies(response)
    return {"message": "Logged out"}
