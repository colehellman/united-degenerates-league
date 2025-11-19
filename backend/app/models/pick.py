from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.session import Base


class Pick(Base):
    """Daily Picks - user's prediction for a specific game"""
    __tablename__ = "picks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False, index=True)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id"), nullable=False, index=True)

    # Prediction
    predicted_winner_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)

    # Locking
    is_locked = Column(Boolean, default=False, nullable=False, index=True)
    locked_at = Column(DateTime, nullable=True)

    # Scoring
    is_correct = Column(Boolean, nullable=True)  # NULL until game is final
    points_earned = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="picks")
    competition = relationship("Competition", back_populates="picks")
    game = relationship("Game", back_populates="picks")

    # Constraints
    __table_args__ = (
        # One pick per user per game per competition
        CheckConstraint("user_id IS NOT NULL AND competition_id IS NOT NULL AND game_id IS NOT NULL"),
    )


class FixedTeamSelection(Base):
    """Fixed Teams - user's pre-selected teams or golfers for the entire competition"""
    __tablename__ = "fixed_team_selections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False, index=True)

    # Either team_id OR golfer_id, not both
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    golfer_id = Column(UUID(as_uuid=True), ForeignKey("golfers.id"), nullable=True, index=True)

    # Locking
    is_locked = Column(Boolean, default=False, nullable=False, index=True)
    locked_at = Column(DateTime, nullable=True)

    # Scoring (calculated differently for team sports vs PGA)
    total_points = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="fixed_team_selections")
    competition = relationship("Competition", back_populates="fixed_team_selections")
    team = relationship("Team", back_populates="fixed_team_selections")
    golfer = relationship("Golfer", back_populates="fixed_team_selections")

    # Constraints
    __table_args__ = (
        # Must have either team_id or golfer_id, but not both
        CheckConstraint("(team_id IS NOT NULL AND golfer_id IS NULL) OR (team_id IS NULL AND golfer_id IS NOT NULL)"),
    )
