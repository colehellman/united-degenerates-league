import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class InviteLink(Base):
    """A shareable invite link for a competition."""

    __tablename__ = "invite_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    competition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    token = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(9),
    )
    is_admin_invite = Column(Boolean, nullable=False, default=False)
    use_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    competition = relationship("Competition", back_populates="invite_links")
    created_by = relationship("User")
