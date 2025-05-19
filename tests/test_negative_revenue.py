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

    store_svc = StoreService(session)
    user_svc = UserService(session)
    rev_svc = RevenueService(session)

    store = await store_svc.get_or_create("NegativeTestStore")
    manager = await user_svc.get_or_create(
        "Negative", "Test", "manager", store_id=store.id
    )

    await store_svc.set_plan(store, 10000.0)

    revenue_repo = RevenueRepository(session)
    today = date.today()

    positive_revenue = await revenue_repo.create(
        amount=5000.0, store_id=store.id, manager_id=manager.id, date_=today
    )

    assert positive_revenue.amount == 5000.0

    negative_revenue = await revenue_repo.create(
        amount=-1000.0, store_id=store.id, manager_id=manager.id, date_=today
    )

    assert negative_revenue.amount == -1000.0

    sum_amount = await revenue_repo.get_sum_for_period(
        store_id=store.id, start_date=today, end_date=today
    )

    assert sum_amount == -1000.0


@pytest.mark.asyncio
async def test_matryoshka_with_negative_revenue(session):
    """Тест визуализации матрешки с отрицательной выручкой"""

    store_svc = StoreService(session)
    user_svc = UserService(session)
    rev_svc = RevenueService(session)

    store = await store_svc.get_or_create("MatryoshkaNegStore")
    manager = await user_svc.get_or_create(
        "Matryoshka", "Negative", "manager", store_id=store.id
    )

    await store_svc.set_plan(store, 10000.0)

    revenue_repo = RevenueRepository(session)
    today = date.today()

    await revenue_repo.create(
        amount=3000.0, store_id=store.id, manager_id=manager.id, date_=today
    )
    await revenue_repo.create(
        amount=-500.0, store_id=store.id, manager_id=manager.id, date_=today
    )

    matryoshka_data = await rev_svc.get_matryoshka_data()

    store_data = next(
        (item for item in matryoshka_data if item["title"] == "MatryoshkaNegStore"),
        None,
    )

    assert store_data is not None

    expected_amount = -500.0
    assert (
        float(store_data["total_amount"].replace(" ₽", "").replace(" ", ""))
        == expected_amount
    )

    assert store_data["fill_percent"] == -5.0
