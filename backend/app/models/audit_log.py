import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class AuditAction(str, enum.Enum):
    # Competition actions
    COMPETITION_CREATED = "competition_created"
    COMPETITION_DELETED = "competition_deleted"
    COMPETITION_STATUS_CHANGED = "competition_status_changed"
    COMPETITION_SETTINGS_CHANGED = "competition_settings_changed"

    # User actions
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"

    # Admin actions
    ADMIN_ADDED = "admin_added"
    ADMIN_REMOVED = "admin_removed"

    # Score corrections
    SCORE_CORRECTED = "score_corrected"

    # Winner designation
    WINNER_DESIGNATED = "winner_designated"

    # Participant actions
    PARTICIPANT_REMOVED = "participant_removed"

    # Join requests
    JOIN_REQUEST_APPROVED = "join_request_approved"
    JOIN_REQUEST_REJECTED = "join_request_rejected"

    # User account actions
    USER_SUSPENDED = "user_suspended"
    USER_BANNED = "user_banned"
    USER_REACTIVATED = "user_reactivated"


class AuditLog(Base):
    """Immutable audit log for admin actions"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Who performed the action
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # What action was performed
    action = Column(Enum(AuditAction), nullable=False, index=True)

    # What was the target (competition, user, game, etc.)
    target_type = Column(String, nullable=False)  # e.g., "competition", "user", "game"
    target_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Additional details (before/after values, justification, etc.)
    details = Column(JSON, nullable=True)

    # Timestamp (UTC)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # No relationships needed - audit logs are immutable and don't cascade delete
