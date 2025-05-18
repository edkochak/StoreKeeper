import pytest
from datetime import date
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.services.revenue_service import RevenueService
from app.models.revenue import Revenue


@pytest.mark.asyncio
async def test_get_month_total(session):
    """Тест расчета суммарной выручки за месяц"""
    # Создаем магазин и менеджера для теста
    store_svc = StoreService(session)
    user_svc = UserService(session)
    rev_svc = RevenueService(session)

    store = await store_svc.get_or_create("MonthTotalStore")
    manager = await user_svc.get_or_create(
        "Month", "Total", "manager", store_id=store.id
    )

    # Добавляем несколько записей о выручке за разные даты
    # В текущем месяце
    current_year = date.today().year
    current_month = date.today().month

    # Текущий месяц, записи суммой 1000
    await rev_svc.create_revenue(
        500.0, store.id, manager.id, date(current_year, current_month, 10)
    )
    await rev_svc.create_revenue(
        500.0, store.id, manager.id, date(current_year, current_month, 20)
    )

    # Прошлый месяц, запись на 300
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    await rev_svc.create_revenue(
        300.0, store.id, manager.id, date(prev_year, prev_month, 15)
    )

    # Проверяем суммарную выручку за текущий месяц
    total = await rev_svc.get_month_total(store.id)
    assert total == 1000.0

    # Проверяем суммарную выручку за прошлый месяц
    total_prev = await rev_svc.get_month_total(store.id, prev_month, prev_year)
    assert total_prev == 300.0

    # Проверяем суммарную выручку за месяц без данных
    future_month = current_month + 1 if current_month < 12 else 1
    future_year = current_year if current_month < 12 else current_year + 1
    total_future = await rev_svc.get_month_total(store.id, future_month, future_year)
    assert total_future == 0.0
