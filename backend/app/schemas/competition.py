from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional, List
from app.models.competition import CompetitionMode, CompetitionStatus, Visibility, JoinType


class CompetitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    mode: CompetitionMode
    league_id: UUID4
    start_date: datetime
    end_date: datetime
    display_timezone: str = "UTC"
    visibility: Visibility = Visibility.PRIVATE
    join_type: JoinType = JoinType.REQUIRES_APPROVAL
    max_participants: Optional[int] = None
    max_picks_per_day: Optional[int] = None
    max_teams_per_participant: Optional[int] = None
    max_golfers_per_participant: Optional[int] = None


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    display_timezone: Optional[str] = None
    visibility: Optional[Visibility] = None
    join_type: Optional[JoinType] = None
    max_participants: Optional[int] = None
    max_picks_per_day: Optional[int] = None
    status: Optional[CompetitionStatus] = None


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
