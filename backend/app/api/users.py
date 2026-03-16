from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from datetime import datetime, timedelta

from app.core.deps import get_db, get_current_user
from app.models.user import User, AccountStatus
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.core.security import verify_password, get_password_hash
from app.services.token_blacklist import blacklist_all_user_tokens

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile"""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile"""
    if update_data.username is not None:
        # Check uniqueness before updating
        result = await db.execute(
            select(User).where(User.username == update_data.username, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        current_user.username = update_data.username

    if update_data.has_dismissed_onboarding is not None:
        current_user.has_dismissed_onboarding = update_data.has_dismissed_onboarding

    current_user.updated_at = datetime.utcnow()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post("/me/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password"""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    await db.commit()

    # Revoke all existing refresh tokens so stolen tokens can't be reused
    blacklist_all_user_tokens(str(current_user.id))

    return {"message": "Password updated successfully"}


@router.delete("/me")
async def request_account_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request account deletion (30-day grace period)"""
    current_user.status = AccountStatus.PENDING_DELETION
    current_user.deletion_requested_at = datetime.utcnow()
    current_user.updated_at = datetime.utcnow()
    await db.commit()

    # Revoke all existing refresh tokens
    blacklist_all_user_tokens(str(current_user.id))

    deletion_date = current_user.deletion_requested_at + timedelta(days=30)

    return {
        "message": "Account deletion requested",
        "deletion_date": deletion_date,
        "grace_period_days": 30,
    }


@router.post("/me/cancel-deletion")
async def cancel_account_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel account deletion request"""
    if current_user.status != AccountStatus.PENDING_DELETION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending deletion request",
        )

    current_user.status = AccountStatus.ACTIVE
    current_user.deletion_requested_at = None
    current_user.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Account deletion cancelled"}
