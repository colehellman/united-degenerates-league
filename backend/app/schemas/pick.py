from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List


class PickCreate(BaseModel):
    game_id: UUID4
    predicted_winner_team_id: UUID4


class PickBatchCreate(BaseModel):
    picks: List[PickCreate]


class PickUpdate(BaseModel):
    predicted_winner_team_id: UUID4


class PickResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    game_id: UUID4
    predicted_winner_team_id: UUID4
    is_locked: bool
    locked_at: Optional[datetime] = None
    is_correct: Optional[bool] = None
    points_earned: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FixedTeamSelectionCreate(BaseModel):
    team_id: Optional[UUID4] = None
    golfer_id: Optional[UUID4] = None


class FixedTeamSelectionBatchCreate(BaseModel):
    selections: List[FixedTeamSelectionCreate]


class FixedTeamSelectionResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    team_id: Optional[UUID4] = None
    golfer_id: Optional[UUID4] = None
    is_locked: bool
    locked_at: Optional[datetime] = None
    total_points: int
    created_at: datetime

    class Config:
        from_attributes = True
