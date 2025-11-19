from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.session import Base


class LeagueName(str, enum.Enum):
    NFL = "NFL"
    NBA = "NBA"
    MLB = "MLB"
    NHL = "NHL"
    NCAA_BASKETBALL = "NCAA_BASKETBALL"
    NCAA_FOOTBALL = "NCAA_FOOTBALL"
    PGA = "PGA"
    MLS = "MLS"  # v2
    EPL = "EPL"  # v2
    UCL = "UCL"  # v2


class League(Base):
    __tablename__ = "leagues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(Enum(LeagueName), unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)  # e.g., "National Football League"

    # For team-based sports
    is_team_based = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    competitions = relationship("Competition", back_populates="league")
    teams = relationship("Team", back_populates="league", cascade="all, delete-orphan")
    golfers = relationship("Golfer", back_populates="league", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    league_id = Column(UUID(as_uuid=True), ForeignKey("leagues.id"), nullable=False, index=True)

    # Team identification
    external_id = Column(String, nullable=False, index=True)  # ID from external API
    name = Column(String, nullable=False)
    abbreviation = Column(String, nullable=False)
    city = Column(String, nullable=True)

    # Logo and colors
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)

    # Active status
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    league = relationship("League", back_populates="teams")
    home_games = relationship("Game", back_populates="home_team", foreign_keys="Game.home_team_id")
    away_games = relationship("Game", back_populates="away_team", foreign_keys="Game.away_team_id")
    fixed_team_selections = relationship("FixedTeamSelection", back_populates="team")


class Golfer(Base):
    __tablename__ = "golfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    league_id = Column(UUID(as_uuid=True), ForeignKey("leagues.id"), nullable=False, index=True)

    # Golfer identification
    external_id = Column(String, nullable=False, index=True)  # ID from PGA API
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    full_name = Column(String, nullable=False, index=True)

    # Photo
    photo_url = Column(String, nullable=True)

    # Active status
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    league = relationship("League", back_populates="golfers")
    fixed_team_selections = relationship("FixedTeamSelection", back_populates="golfer")
