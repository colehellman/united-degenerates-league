from datetime import datetime

from pydantic import UUID4, BaseModel, Field


class PickCreate(BaseModel):
    game_id: UUID4
    predicted_winner_team_id: UUID4


class PickBatchCreate(BaseModel):
    picks: list[PickCreate] = Field(..., max_length=50)


class PickUpdate(BaseModel):
    predicted_winner_team_id: UUID4


class PickResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    game_id: UUID4
    predicted_winner_team_id: UUID4
    is_locked: bool
    locked_at: datetime | None = None
    is_correct: bool | None = None
    points_earned: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FixedTeamSelectionCreate(BaseModel):
    team_id: UUID4 | None = None
    golfer_id: UUID4 | None = None


class FixedTeamSelectionBatchCreate(BaseModel):
    selections: list[FixedTeamSelectionCreate] = Field(..., max_length=50)


class FixedTeamSelectionResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    team_id: UUID4 | None = None
    golfer_id: UUID4 | None = None
    is_locked: bool
    locked_at: datetime | None = None
    total_points: int
    created_at: datetime

    class Config:
        from_attributes = True
