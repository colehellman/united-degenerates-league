from datetime import datetime

from pydantic import UUID4, BaseModel


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
    last_pick_at: datetime | None = None

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


class ParticipantWithUserResponse(BaseModel):
    """Participant record joined with basic user info, used in admin views.

    Deliberately omits email — competition admins are not global admins
    and should not see other users' email addresses.
    """

    id: UUID4
    user_id: UUID4
    username: str
    joined_at: datetime
    total_points: int
    total_wins: int
    total_losses: int
    accuracy_percentage: float
    current_streak: int

    class Config:
        from_attributes = True


class JoinRequestCreate(BaseModel):
    competition_id: UUID4


class JoinRequestResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    status: str
    reviewed_by_user_id: UUID4 | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
