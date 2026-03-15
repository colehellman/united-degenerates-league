from pydantic import BaseModel, UUID4, Field
from typing import Optional

from app.models.user import AccountStatus, UserRole
from app.models.competition import CompetitionStatus


class UserStatusUpdate(BaseModel):
    status: AccountStatus
    reason: Optional[str] = Field(None, max_length=500)


class UserRoleUpdate(BaseModel):
    role: UserRole


class ScoreCorrectionRequest(BaseModel):
    home_team_score: int = Field(..., ge=0)
    away_team_score: int = Field(..., ge=0)
    reason: str = Field(..., min_length=1, max_length=500)


class WinnerDesignationRequest(BaseModel):
    winner_user_id: UUID4
    reason: Optional[str] = Field(None, max_length=500)


class CompetitionStatusChange(BaseModel):
    status: CompetitionStatus
    reason: Optional[str] = Field(None, max_length=500)


class AdminManagement(BaseModel):
    user_id: UUID4
