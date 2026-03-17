import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class UserRole(str, enum.Enum):
    USER = "user"
    # LEAGUE_ADMIN is unused — competition-level admin is handled via
    # Competition.league_admin_ids (per-competition array). Kept for DB
    # compatibility but never assigned or checked anywhere.
    LEAGUE_ADMIN = "league_admin"
    GLOBAL_ADMIN = "global_admin"


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING_DELETION = "pending_deletion"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Account deletion
    deletion_requested_at = Column(DateTime, nullable=True)

    # Brute-force protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Onboarding
    has_dismissed_onboarding = Column(Boolean, default=False, nullable=False)

    # Relationships
    participants = relationship("Participant", back_populates="user", cascade="all, delete-orphan")
    picks = relationship("Pick", back_populates="user", cascade="all, delete-orphan")
    fixed_team_selections = relationship(
        "FixedTeamSelection", back_populates="user", cascade="all, delete-orphan"
    )
    created_competitions = relationship(
        "Competition",
        back_populates="creator",
        foreign_keys="Competition.creator_id",
        passive_deletes=True,
    )
    join_requests = relationship(
        "JoinRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="JoinRequest.user_id",
    )
    bug_reports = relationship("BugReport", back_populates="user", cascade="all, delete-orphan")
