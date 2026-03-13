import pytest
from httpx import AsyncClient
from app.main import _seed_leagues_if_empty
from app.models.league import League
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_seed_leagues_if_empty(db_session: AsyncSession):
    """Test seeding leagues when DB is empty."""
    # Ensure empty
    from app.models.league import League
    await db_session.execute(text("TRUNCATE TABLE leagues CASCADE"))
    await db_session.commit()
    
    # Run seeding
    await _seed_leagues_if_empty()
    
    # Verify
    result = await db_session.execute(select(func.count()).select_from(League))
    count = result.scalar()
    assert count > 0
    
    # Run again (should be idempotent)
    await _seed_leagues_if_empty()
    result2 = await db_session.execute(select(func.count()).select_from(League))
    assert result2.scalar() == count

from sqlalchemy import text
