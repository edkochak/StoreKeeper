import pytest
from datetime import date
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.services.revenue_service import RevenueService
from app.repositories.revenue_repository import RevenueRepository
from app.models.revenue import Revenue


@pytest.mark.asyncio
async def test_negative_revenue_creation(session):
    """Тест для проверки создания и обработки отрицательной выручки"""

    # Инициализация необходимых сервисов
    store_svc = StoreService(session)
    user_svc = UserService(session)
    rev_svc = RevenueService(session)

    # Создаем тестовый магазин и менеджера
    store = await store_svc.get_or_create("NegativeTestStore")
    manager = await user_svc.get_or_create(
        "Negative", "Test", "manager", store_id=store.id
    )

    # Устанавливаем план для магазина
    await store_svc.set_plan(store, 10000.0)

    # Добавляем положительную выручку
    revenue_repo = RevenueRepository(session)
    today = date.today()

    positive_revenue = await revenue_repo.create(
        amount=5000.0, store_id=store.id, manager_id=manager.id, date_=today
    )

    # Проверяем, что выручка добавлена
    assert positive_revenue.amount == 5000.0

    # Добавляем отрицательную выручку (возврат)
    negative_revenue = await revenue_repo.create(
        amount=-1000.0, store_id=store.id, manager_id=manager.id, date_=today
    )

    # Проверяем, что отрицательная выручка добавлена
    assert negative_revenue.amount == -1000.0

    # Получаем сумму выручки за сегодня
    sum_amount = await revenue_repo.get_sum_for_period(
        store_id=store.id, start_date=today, end_date=today
    )

    # Проверяем, что сумма учитывает отрицательную выручку
    assert sum_amount == 4000.0  # 5000 - 1000 = 4000


@pytest.mark.asyncio
async def test_matryoshka_with_negative_revenue(session):
    """Тест визуализации матрешки с отрицательной выручкой"""

    # Инициализация необходимых сервисов
    store_svc = StoreService(session)
    user_svc = UserService(session)
    rev_svc = RevenueService(session)

    # Создаем тестовый магазин и менеджера
    store = await store_svc.get_or_create("MatryoshkaNegStore")
    manager = await user_svc.get_or_create(
        "Matryoshka", "Negative", "manager", store_id=store.id
    )

    # Устанавливаем план для магазина
    await store_svc.set_plan(store, 10000.0)

    # Добавляем выручку с учетом отрицательных значений
    revenue_repo = RevenueRepository(session)
    today = date.today()

    # Симулируем ситуацию с продажами и возвратами
    await revenue_repo.create(
        amount=3000.0, store_id=store.id, manager_id=manager.id, date_=today
    )
    await revenue_repo.create(
        amount=-500.0, store_id=store.id, manager_id=manager.id, date_=today
    )

    # Получаем данные для матрешки
    matryoshka_data = await rev_svc.get_matryoshka_data()

    # Ищем наш магазин в данных
    store_data = next(
        (item for item in matryoshka_data if item["title"] == "MatryoshkaNegStore"),
        None,
    )

    # Проверяем данные
    assert store_data is not None

    # Сумма должна быть с учетом отрицательной выручки
    expected_amount = 2500.0  # 3000 - 500
    assert (
        float(store_data["total_amount"].replace(" ₽", "").replace(" ", ""))
        == expected_amount
    )

    # Проверяем процент выполнения плана (должен быть 25%)
    assert store_data["fill_percent"] == 25
