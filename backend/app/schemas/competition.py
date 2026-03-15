from pydantic import BaseModel, Field, UUID4, field_validator
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from app.models.competition import CompetitionMode, CompetitionStatus, Visibility, JoinType


class CompetitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    mode: CompetitionMode
    league_id: UUID4
    start_date: datetime
    end_date: datetime

    @field_validator("start_date", "end_date", mode="after")
    @classmethod
    def strip_timezone(cls, v: datetime) -> datetime:
        """Convert tz-aware datetimes to naive UTC.

        The database uses TIMESTAMP WITHOUT TIME ZONE, so asyncpg rejects
        mixing tz-aware values (from JSON 'Z' suffix) with naive values
        (from datetime.utcnow defaults on created_at/updated_at).
        """
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v
    display_timezone: str = "UTC"
    visibility: Visibility = Visibility.PRIVATE
    join_type: JoinType = JoinType.REQUIRES_APPROVAL
    max_participants: Optional[int] = None
    max_picks_per_day: Optional[int] = None
    max_teams_per_participant: Optional[int] = None
    max_golfers_per_participant: Optional[int] = None


class CompetitionCreate(CompetitionBase):
    @field_validator("start_date", mode="after")
    @classmethod
    def start_date_not_in_past(cls, v: datetime) -> datetime:
        """Reject start dates more than 60 seconds in the past.

        The 60-second grace window absorbs clock skew and form-submission
        latency without letting users accidentally create competitions dated
        hours or days ago.  strip_timezone (inherited from CompetitionBase)
        has already normalized v to naive UTC before this runs.
        """
        if v < datetime.utcnow() - timedelta(seconds=60):
            raise ValueError("Start date cannot be in the past")
        return v


class CompetitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("start_date", "end_date", mode="after")
    @classmethod
    def strip_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Same naive-UTC normalization as CompetitionBase."""
        if v is not None and v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v
    display_timezone: Optional[str] = None
    visibility: Optional[Visibility] = None
    join_type: Optional[JoinType] = None
    max_participants: Optional[int] = None
    max_picks_per_day: Optional[int] = None
    # status is intentionally excluded — competition lifecycle transitions
    # are managed by background jobs only (UPCOMING → ACTIVE → COMPLETED).
    # Allowing admins to set status directly would bypass the intended flow.


class CompetitionResponse(CompetitionBase):
    id: UUID4
    status: CompetitionStatus
    creator_id: UUID4
    league_admin_ids: List[UUID4]
    winner_user_id: Optional[UUID4] = None
    created_at: datetime
    updated_at: datetime
    participant_count: Optional[int] = None
    user_is_participant: Optional[bool] = None
    user_is_admin: Optional[bool] = None

    class Config:
        from_attributes = True


class CompetitionListResponse(BaseModel):
    id: UUID4
    name: str
    mode: CompetitionMode
    status: CompetitionStatus
    league_id: UUID4
    start_date: datetime
    end_date: datetime
    visibility: Visibility
    participant_count: int
    max_participants: Optional[int] = None
    user_is_participant: bool

    class Config:
        from_attributes = True
