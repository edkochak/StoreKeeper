"""
Тест исправлений для команд администратора и месячных планов
"""

import pytest
from datetime import date
from app.models.monthly_plan import MonthlyPlan
from app.repositories.monthly_plan_repository import MonthlyPlanRepository
from app.services.revenue_service import RevenueService
from app.services.store_service import StoreService


@pytest.mark.asyncio
async def test_monthly_plan_date_type_fix(session):
    """Тест что поле month_year правильно работает с типом Date"""
    store_service = StoreService(session)
    store = await store_service.get_or_create("TestDateTypeStore")

    repo = MonthlyPlanRepository(session)

    test_date = date(2025, 12, 1)
    plan = await repo.create_plan(store.id, test_date, 50000.0)

    assert plan.month_year == test_date
    assert isinstance(plan.month_year, date)

    found_plan = await repo.get_plan(store.id, test_date)
    assert found_plan is not None
    assert found_plan.id == plan.id
    assert found_plan.month_year == test_date


@pytest.mark.asyncio
async def test_revenue_service_integration_with_fixed_types(session):
    """Тест интеграции RevenueService с исправленными типами"""
    store_service = StoreService(session)
    revenue_service = RevenueService(session)

    store = await store_service.get_or_create("TestIntegrationStore")

    success = await revenue_service.set_monthly_plan(store.id, 12, 2025, 75000.0)
    assert success is True

    plan_amount = await revenue_service.get_monthly_plan(store.id, 12, 2025)
    assert plan_amount == 75000.0

    status = await revenue_service.get_status(store.id, 12, 2025)
    assert status is not None
    assert status["plan"] == 75000.0
