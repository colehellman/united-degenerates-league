from fastapi import APIRouter, Depends
from app.core.deps import get_current_user, get_current_global_admin
from app.models.user import User
from app.services.sports_api.sports_service import sports_service

router = APIRouter()


@router.get("/api-status")
async def get_api_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get status of all sports data APIs and circuit breakers.

    Available to all authenticated users.
    """
    return sports_service.get_api_health_status()


@router.post("/reset-circuit-breakers")
async def reset_circuit_breakers(
    current_user: User = Depends(get_current_global_admin),
):
    """
    Manually reset all circuit breakers.

    Only available to global admins.
    """
    from app.services.circuit_breaker import circuit_breaker_manager

    circuit_breaker_manager.reset_all()

    return {
        "message": "All circuit breakers have been reset",
        "status": circuit_breaker_manager.get_all_status(),
    }
