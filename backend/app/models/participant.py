from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class JoinRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Participant(Base):
    """Represents a user's participation in a specific competition"""
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False, index=True)

    # Scoring
    total_points = Column(Integer, default=0, nullable=False, index=True)
    total_wins = Column(Integer, default=0, nullable=False)
    total_losses = Column(Integer, default=0, nullable=False)
    accuracy_percentage = Column(Float, default=0.0, nullable=False)  # For sorting leaderboard

    # Current streak (optional, v2 feature)
    current_streak = Column(Integer, default=0, nullable=False)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_pick_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="participants")
    competition = relationship("Competition", back_populates="participants")


class JoinRequest(Base):
    """Join request for competitions with requiresApproval join type"""
    __tablename__ = "join_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False, index=True)

    status = Column(Enum(JoinRequestStatus), default=JoinRequestStatus.PENDING, nullable=False, index=True)

    # Approval/rejection
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="join_requests", foreign_keys=[user_id])
    competition = relationship("Competition", back_populates="join_requests")


# Need to import String for rejection_reason
from sqlalchemy import String
