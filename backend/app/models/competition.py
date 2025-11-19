from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class CompetitionMode(str, enum.Enum):
    DAILY_PICKS = "daily_picks"
    FIXED_TEAMS = "fixed_teams"


class CompetitionStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"


class Visibility(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class JoinType(str, enum.Enum):
    OPEN = "open"
    REQUIRES_APPROVAL = "requires_approval"


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Mode and status
    mode = Column(Enum(CompetitionMode), nullable=False)
    status = Column(Enum(CompetitionStatus), default=CompetitionStatus.UPCOMING, nullable=False, index=True)

    # Associated league (NFL, NBA, etc.)
    league_id = Column(UUID(as_uuid=True), ForeignKey("leagues.id"), nullable=False, index=True)

    # Date range
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)

    # Display timezone (IANA format, e.g., "America/New_York")
    display_timezone = Column(String, default="UTC", nullable=False)

    # Visibility and joining
    visibility = Column(Enum(Visibility), default=Visibility.PRIVATE, nullable=False)
    join_type = Column(Enum(JoinType), default=JoinType.REQUIRES_APPROVAL, nullable=False)
    max_participants = Column(Integer, nullable=True)  # NULL = unlimited

    # Daily Picks settings
    max_picks_per_day = Column(Integer, nullable=True)  # Only for daily_picks mode

    # Fixed Teams settings
    max_teams_per_participant = Column(Integer, nullable=True)  # Only for fixed_teams mode (team sports)
    max_golfers_per_participant = Column(Integer, nullable=True)  # Only for PGA tournaments

    # Creator and admins
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    league_admin_ids = Column(ARRAY(UUID(as_uuid=True)), default=[], nullable=False)  # Additional admins

    # Winner (set manually after tie-breaker if needed)
    winner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    league = relationship("League", back_populates="competitions")
    creator = relationship("User", back_populates="created_competitions", foreign_keys=[creator_id])
    participants = relationship("Participant", back_populates="competition", cascade="all, delete-orphan")
    games = relationship("Game", back_populates="competition", cascade="all, delete-orphan")
    picks = relationship("Pick", back_populates="competition", cascade="all, delete-orphan")
    fixed_team_selections = relationship("FixedTeamSelection", back_populates="competition", cascade="all, delete-orphan")
    join_requests = relationship("JoinRequest", back_populates="competition", cascade="all, delete-orphan")
