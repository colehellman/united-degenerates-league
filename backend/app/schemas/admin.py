from pydantic import UUID4, BaseModel, Field

from app.models.competition import CompetitionStatus
from app.models.user import AccountStatus, UserRole


class UserStatusUpdate(BaseModel):
    status: AccountStatus
    reason: str | None = Field(None, max_length=500)


class UserRoleUpdate(BaseModel):
    role: UserRole


class ScoreCorrectionRequest(BaseModel):
    home_team_score: int = Field(..., ge=0)
    away_team_score: int = Field(..., ge=0)
    reason: str = Field(..., min_length=1, max_length=500)


class WinnerDesignationRequest(BaseModel):
    winner_user_id: UUID4
    reason: str | None = Field(None, max_length=500)


class CompetitionStatusChange(BaseModel):
    status: CompetitionStatus
    reason: str | None = Field(None, max_length=500)


class AdminManagement(BaseModel):
    user_id: UUID4
