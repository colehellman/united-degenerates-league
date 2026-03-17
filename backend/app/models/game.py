import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class GameStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    NO_RESULT = "no_result"


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("competition_id", "external_id", name="uq_game_competition_external_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    competition_id = Column(
        UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False, index=True
    )

    # External API identification
    external_id = Column(String, nullable=False, index=True)  # ID from sports API

    # Teams
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)

    # Timing (always stored in UTC)
    scheduled_start_time = Column(DateTime, nullable=False, index=True)
    actual_start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Status
    status = Column(Enum(GameStatus), default=GameStatus.SCHEDULED, nullable=False, index=True)

    # Scores
    home_team_score = Column(Integer, nullable=True)
    away_team_score = Column(Integer, nullable=True)

    # Winner (NULL if tie, cancelled, or no result)
    winner_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)

    # Venue
    venue_name = Column(String, nullable=True)
    venue_city = Column(String, nullable=True)

    # Betting odds — sourced from ESPN (DraftKings) on each sync cycle.
    # spread is from the home team's perspective: negative = home favored.
    # Both nullable; not all leagues/providers supply odds data.
    spread = Column(Float, nullable=True)
    over_under = Column(Float, nullable=True)

    # Additional data from API (stored as JSON)
    api_data = Column(JSON, nullable=True)

    # Scoring state — set to True after picks are successfully scored.
    # Used by the background job to retry scoring on FINAL games that failed.
    scoring_completed = Column(Boolean, default=False, nullable=False, index=True)

    # Score correction tracking
    score_corrected_at = Column(DateTime, nullable=True)
    score_correction_count = Column(Integer, default=0, nullable=False)  # Max 1 per spec

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    competition = relationship("Competition", back_populates="games")
    home_team = relationship("Team", back_populates="home_games", foreign_keys=[home_team_id])
    away_team = relationship("Team", back_populates="away_games", foreign_keys=[away_team_id])
    picks = relationship("Pick", back_populates="game", cascade="all, delete-orphan")
