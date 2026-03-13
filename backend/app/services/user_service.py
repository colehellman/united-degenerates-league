import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.models.user import User, AccountStatus

logger = logging.getLogger(__name__)

async def cleanup_pending_deletions(db):
    """
    Background job to permanently delete accounts after 30-day grace period.
    """
    logger.info(f"Running account deletion cleanup job at {datetime.utcnow()}")
    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)

    # Find users pending deletion past grace period
    stmt = (
        select(User)
        .where(
            and_(
                User.status == AccountStatus.PENDING_DELETION,
                User.deletion_requested_at <= cutoff
            )
        )
    )
    result = await db.execute(stmt)
    users_to_delete = result.scalars().all()

    if not users_to_delete:
        logger.info("No pending deletions to process")
        return

    logger.info(f"Found {len(users_to_delete)} accounts to delete")

    for user in users_to_delete:
        # Anonymize user data
        user.email = f"deleted_user_{user.id}@deleted.local"
        user.username = f"Deleted User #{user.id}"
        user.hashed_password = ""
        user.status = AccountStatus.DELETED
        user.updated_at = now

        logger.info(f"Deleted and anonymized user {user.id}")
