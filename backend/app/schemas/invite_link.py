from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

from app.models.competition import CompetitionMode, CompetitionStatus


class InviteLinkResponse(BaseModel):
    """Response for created/listed invite links."""
    id: UUID4
    token: str
    is_admin_invite: bool
    use_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class InviteResolveResponse(BaseModel):
    """Response for resolving an invite token — limited competition info."""
    competition_id: UUID4
    competition_name: str
    description: Optional[str] = None
    league_display_name: str
    mode: CompetitionMode
    status: CompetitionStatus
    participant_count: int
    max_participants: Optional[int] = None
    is_admin_invite: bool


class JoinCompetitionRequest(BaseModel):
    """Optional request body for joining a competition with an invite token."""
    invite_token: Optional[str] = None
