"""
Тесты для функциональности месячных планов
"""

import pytest
from datetime import datetime, date
from app.models.monthly_plan import MonthlyPlan
from app.repositories.monthly_plan_repository import MonthlyPlanRepository
from app.services.revenue_service import RevenueService
from app.services.store_service import StoreService


@pytest.mark.asyncio
async def test_monthly_plan_model(session):
    """Тест модели MonthlyPlan"""
    store_service = StoreService(session)
    store = await store_service.get_or_create("TestPlanStore")

    plan = MonthlyPlan(
        store_id=store.id, month_year=date(2025, 6, 1), plan_amount=50000.0
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    assert plan.id is not None
    assert plan.store_id == store.id
    assert plan.month_year == date(2025, 6, 1)
    assert plan.plan_amount == 50000.0


@pytest.mark.asyncio
async def test_monthly_plan_repository_crud(session):
    """Тест CRUD операций в MonthlyPlanRepository"""
    store_service = StoreService(session)
    store = await store_service.get_or_create("TestCrudStore")

    repo = MonthlyPlanRepository(session)

    plan = await repo.create_plan(store.id, date(2025, 7, 1), 60000.0)
    assert plan.store_id == store.id
    assert plan.month_year == date(2025, 7, 1)
    assert plan.plan_amount == 60000.0

    found_plan = await repo.get_plan(store.id, date(2025, 7, 1))
    assert found_plan is not None
    assert found_plan.id == plan.id

    updated_plan = await repo.update_plan(store.id, date(2025, 7, 1), 75000.0)
    assert updated_plan.plan_amount == 75000.0

    await repo.delete_plan(store.id, date(2025, 7, 1))
    deleted_plan = await repo.get_plan(store.id, date(2025, 7, 1))
    assert deleted_plan is None


@pytest.mark.asyncio
async def test_monthly_plan_unique_constraint(session):
    """Тест уникального ограничения store_id + month_year"""
    store_service = StoreService(session)
    store = await store_service.get_or_create("TestUniqueStore")

    repo = MonthlyPlanRepository(session)

    plan1 = await repo.create_plan(store.id, date(2025, 8, 1), 40000.0)
    assert plan1 is not None

    plan2 = await repo.update_plan(store.id, date(2025, 8, 1), 50000.0)

    updated_plan = await repo.get_plan(store.id, date(2025, 8, 1))
    assert updated_plan.id == plan1.id
    assert updated_plan.plan_amount == 50000.0


@pytest.mark.asyncio
async def test_revenue_service_monthly_plans(session):
    """Тест интеграции месячных планов в RevenueService"""
    store_service = StoreService(session)
    revenue_service = RevenueService(session)

    store = await store_service.get_or_create("TestServiceStore")

    result = await revenue_service.set_monthly_plan(store.id, 6, 2025, 80000.0)
    assert result is True

    plan_amount = await revenue_service.get_monthly_plan(store.id, 6, 2025)
    assert plan_amount == 80000.0

    await store_service.set_plan(store, 90000.0)
    fallback_plan = await revenue_service.get_monthly_plan(store.id, 7, 2025)
    assert fallback_plan == 90000.0


@pytest.mark.asyncio
async def test_get_status_with_monthly_plan(session):
    """Тест получения статуса с месячными планами"""
    store_service = StoreService(session)
    revenue_service = RevenueService(session)

    store = await store_service.get_or_create("TestStatusStore")

    await revenue_service.set_monthly_plan(store.id, 6, 2025, 100000.0)

    status = await revenue_service.get_status(store.id, 6, 2025)
    assert status is not None
    assert status["plan"] == 100000.0
    assert status["total"] == 0.0
    assert status["percent"] == 0
