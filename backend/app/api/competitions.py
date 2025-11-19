from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime

from app.core.deps import get_db, get_current_user, get_current_global_admin
from app.models.user import User
from app.models.competition import Competition, CompetitionStatus, Visibility
from app.models.participant import Participant, JoinRequest, JoinRequestStatus
from app.schemas.competition import (
    CompetitionCreate,
    CompetitionResponse,
    CompetitionUpdate,
    CompetitionListResponse,
)
from app.schemas.participant import JoinRequestCreate, JoinRequestResponse

router = APIRouter()


@router.post("", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
async def create_competition(
    competition_data: CompetitionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new competition"""
    # Validate dates
    if competition_data.end_date <= competition_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Create competition
    competition = Competition(
        **competition_data.model_dump(),
        creator_id=current_user.id,
        league_admin_ids=[str(current_user.id)],  # Creator is default admin
        status=CompetitionStatus.UPCOMING,
    )

    db.add(competition)
    await db.commit()
    await db.refresh(competition)

    # Automatically add creator as participant
    participant = Participant(
        user_id=current_user.id,
        competition_id=competition.id,
    )
    db.add(participant)
    await db.commit()

    response = CompetitionResponse.model_validate(competition)
    response.participant_count = 1
    response.user_is_participant = True
    response.user_is_admin = True

    return response


@router.get("", response_model=List[CompetitionListResponse])
async def list_competitions(
    status_filter: Optional[CompetitionStatus] = None,
    visibility: Optional[Visibility] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all competitions accessible to the current user"""
    query = select(Competition)

    # Filter by status if provided
    if status_filter:
        query = query.where(Competition.status == status_filter)

    # Filter by visibility
    if visibility:
        query = query.where(Competition.visibility == visibility)
    else:
        # Show public competitions and private ones where user is a participant
        query = query.where(
            or_(
                Competition.visibility == Visibility.PUBLIC,
                Competition.id.in_(
                    select(Participant.competition_id).where(
                        Participant.user_id == current_user.id
                    )
                ),
            )
        )

    result = await db.execute(query)
    competitions = result.scalars().all()

    # Get participant counts
    response_list = []
    for comp in competitions:
        count_result = await db.execute(
            select(func.count(Participant.id)).where(
                Participant.competition_id == comp.id
            )
        )
        participant_count = count_result.scalar()

        # Check if user is participant
        participant_result = await db.execute(
            select(Participant).where(
                and_(
                    Participant.competition_id == comp.id,
                    Participant.user_id == current_user.id,
                )
            )
        )
        is_participant = participant_result.scalar_one_or_none() is not None

        comp_response = CompetitionListResponse(
            **{k: getattr(comp, k) for k in CompetitionListResponse.model_fields.keys() if k != 'participant_count' and k != 'user_is_participant'},
            participant_count=participant_count,
            user_is_participant=is_participant,
        )
        response_list.append(comp_response)

    return response_list


@router.get("/{competition_id}", response_model=CompetitionResponse)
async def get_competition(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific competition"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Check if user is participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    is_participant = participant_result.scalar_one_or_none() is not None

    # Get participant count
    count_result = await db.execute(
        select(func.count(Participant.id)).where(
            Participant.competition_id == competition.id
        )
    )
    participant_count = count_result.scalar()

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    response = CompetitionResponse.model_validate(competition)
    response.participant_count = participant_count
    response.user_is_participant = is_participant
    response.user_is_admin = is_admin

    return response


@router.patch("/{competition_id}", response_model=CompetitionResponse)
async def update_competition(
    competition_id: str,
    update_data: CompetitionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a competition (admins only)"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Check if user is admin
    is_admin = (
        str(current_user.id) in competition.league_admin_ids
        or current_user.role == "global_admin"
    )

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only competition admins can update competitions",
        )

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(competition, field, value)

    competition.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(competition)

    return CompetitionResponse.model_validate(competition)


@router.delete("/{competition_id}")
async def delete_competition(
    competition_id: str,
    current_user: User = Depends(get_current_global_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a competition (global admins only)"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    await db.delete(competition)
    await db.commit()

    return {"message": "Competition deleted successfully"}


@router.post("/{competition_id}/join", response_model=JoinRequestResponse)
async def join_competition(
    competition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a competition or request to join"""
    result = await db.execute(
        select(Competition).where(Competition.id == competition_id)
    )
    competition = result.scalar_one_or_none()

    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Check if already a participant
    participant_result = await db.execute(
        select(Participant).where(
            and_(
                Participant.competition_id == competition.id,
                Participant.user_id == current_user.id,
            )
        )
    )
    if participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a participant",
        )

    # Check if max participants reached
    if competition.max_participants:
        count_result = await db.execute(
            select(func.count(Participant.id)).where(
                Participant.competition_id == competition.id
            )
        )
        if count_result.scalar() >= competition.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competition is full",
            )

    # If open join, add participant directly
    if competition.join_type == "open":
        participant = Participant(
            user_id=current_user.id,
            competition_id=competition.id,
        )
        db.add(participant)
        await db.commit()

        return {"message": "Joined competition successfully"}

    # Otherwise, create join request
    join_request = JoinRequest(
        user_id=current_user.id,
        competition_id=competition.id,
        status=JoinRequestStatus.PENDING,
    )
    db.add(join_request)
    await db.commit()
    await db.refresh(join_request)

    return JoinRequestResponse.model_validate(join_request)
