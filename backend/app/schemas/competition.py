from datetime import UTC, datetime

from pydantic import UUID4, BaseModel, Field, field_validator

from app.models.competition import CompetitionMode, CompetitionStatus, JoinType, Visibility


class CompetitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
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
            v = v.astimezone(UTC).replace(tzinfo=None)
        return v

    display_timezone: str = "UTC"
    visibility: Visibility = Visibility.PRIVATE
    join_type: JoinType = JoinType.REQUIRES_APPROVAL
    max_participants: int | None = None
    max_picks_per_day: int | None = None
    max_teams_per_participant: int | None = None
    max_golfers_per_participant: int | None = None


class CompetitionCreate(CompetitionBase):
    @field_validator("start_date", mode="after")
    @classmethod
    def start_date_not_in_past(cls, v: datetime) -> datetime:
        """Reject start dates before today (UTC).

        Compares dates (not datetimes) so that selecting today always works
        regardless of the current time.  strip_timezone (inherited from
        CompetitionBase) has already normalized v to naive UTC before this runs.
        """
        if v.date() < datetime.utcnow().date():
            raise ValueError("Start date cannot be in the past")
        return v


class CompetitionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    @field_validator("start_date", "end_date", mode="after")
    @classmethod
    def strip_timezone(cls, v: datetime | None) -> datetime | None:
        """Same naive-UTC normalization as CompetitionBase."""
        if v is not None and v.tzinfo is not None:
            v = v.astimezone(UTC).replace(tzinfo=None)
        return v

    display_timezone: str | None = None
    visibility: Visibility | None = None
    join_type: JoinType | None = None
    max_participants: int | None = None
    max_picks_per_day: int | None = None
    # status is intentionally excluded — competition lifecycle transitions
    # are managed by background jobs only (UPCOMING → ACTIVE → COMPLETED).
    # Allowing admins to set status directly would bypass the intended flow.


class CompetitionResponse(CompetitionBase):
    id: UUID4
    status: CompetitionStatus
    creator_id: UUID4
    league_admin_ids: list[UUID4]
    winner_user_id: UUID4 | None = None
    created_at: datetime
    updated_at: datetime
    participant_count: int | None = None
    user_is_participant: bool | None = None
    user_is_admin: bool | None = None

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
    max_participants: int | None = None
    user_is_participant: bool

    class Config:
        from_attributes = True
