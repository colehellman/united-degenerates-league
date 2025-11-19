from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class ParticipantResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    total_points: int
    total_wins: int
    total_losses: int
    accuracy_percentage: float
    current_streak: int
    joined_at: datetime
    last_pick_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID4
    username: str
    total_points: int
    total_wins: int
    total_losses: int
    accuracy_percentage: float
    current_streak: int
    is_current_user: bool = False

    class Config:
        from_attributes = True


class JoinRequestCreate(BaseModel):
    competition_id: UUID4


class JoinRequestResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    status: str
    reviewed_by_user_id: Optional[UUID4] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
