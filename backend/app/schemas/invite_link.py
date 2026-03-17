from datetime import datetime

from pydantic import UUID4, BaseModel

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
    description: str | None = None
    league_display_name: str
    mode: CompetitionMode
    status: CompetitionStatus
    participant_count: int
    max_participants: int | None = None
    is_admin_invite: bool


class JoinCompetitionRequest(BaseModel):
    """Optional request body for joining a competition with an invite token."""

    invite_token: str | None = None
