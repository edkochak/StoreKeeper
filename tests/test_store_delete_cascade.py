import pytest
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.services.revenue_service import RevenueService
from datetime import date


@pytest.mark.asyncio
async def test_delete_store_cascade(session):
    store_svc = StoreService(session)
    user_svc = UserService(session)
    revenue_svc = RevenueService(session)

    # Создаём магазин, менеджера и выручку + помесячный план
    store = await store_svc.get_or_create("CascadeStore")
    manager = await user_svc.get_or_create("Cas", "Manager", "manager", store_id=store.id)

    # План на текущий месяц
    today = date.today()
    await revenue_svc.set_monthly_plan(store.id, today.month, today.year, 1000.0)

    # Выручка за сегодня
    await revenue_svc.create_revenue(100.0, store.id, manager.id, today)

    # Проверим, что данные создались
    status_before = await revenue_svc.get_status(store.id)
    assert status_before is not None
    assert status_before["total"] == 100.0

    # Удаляем магазин
    await store_svc.delete_store(store)

    # Проверяем, что магазин удалён и данные очищены/отвязаны
    assert await store_svc.get_by_id(store.id) is None

    # Менеджер должен остаться, но без привязки к магазину
    loaded_manager = await user_svc.get_by_name("Cas", "Manager")
    assert loaded_manager is not None
    assert loaded_manager.store_id is None

    # Статус для удалённого магазина теперь не получить
    status_after = await revenue_svc.get_status(store.id)
    assert status_after is None
