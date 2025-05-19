import pytest
from datetime import date
from sqlalchemy.future import select
from app.repositories.revenue_repository import RevenueRepository
from app.models.revenue import Revenue


@pytest.mark.asyncio
async def test_duplicate_revenue_overwrite(session):
    """При множественных записях за одну дату должна оставаться только последняя запись"""
    repo = RevenueRepository(session)
    today = date.today()

    r1 = await repo.create(amount=100.0, store_id=1, manager_id=1, date_=today)

    r2 = await repo.create(amount=200.0, store_id=1, manager_id=1, date_=today)

    assert r2.id == r1.id
    assert r2.amount == 200.0

    result = await session.execute(select(Revenue).filter_by(store_id=1, date=today))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].amount == 200.0
