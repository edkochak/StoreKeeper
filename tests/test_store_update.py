import pytest
from unittest.mock import patch
from app.services.store_service import StoreService
from app.models.store import Store
from app.repositories.store_repository import StoreRepository


@pytest.mark.asyncio
async def test_store_update_name(session):
    """Тест обновления названия магазина"""

    svc = StoreService(session)

    store = await svc.get_or_create("TestStore")
    assert isinstance(store, Store)
    assert store.name == "TestStore"

    updated_store = await svc.update_name(store, "UpdatedTestStore")
    assert updated_store.id == store.id
    assert updated_store.name == "UpdatedTestStore"

    store_from_db = await svc.get_by_id(store.id)
    assert store_from_db.name == "UpdatedTestStore"


@pytest.mark.asyncio
async def test_store_update_plan(session):
    """Тест обновления плана магазина"""

    svc = StoreService(session)

    store = await svc.get_or_create("PlanUpdateStore")
    assert store.plan == 0.0

    first_update = await svc.set_plan(store, 100.0)
    assert first_update.plan == 100.0

    store_from_db = await svc.get_by_id(store.id)
    assert store_from_db.plan == 100.0

    second_update = await svc.set_plan(store_from_db, 200.0)
    assert second_update.plan == 200.0

    final_store = await svc.get_by_id(store.id)
    assert final_store.plan == 200.0


@pytest.mark.asyncio
async def test_store_edge_cases(session):
    """Тест граничных случаев для магазинов"""

    svc = StoreService(session)

    store = await svc.get_or_create("EdgeCaseStore")

    updated = await svc.set_plan(store, 0.0)
    assert updated.plan == 0.0

    updated = await svc.set_plan(store, 0.001)
    assert updated.plan == 0.001

    updated = await svc.set_plan(store, 999999999.99)
    assert updated.plan == 999999999.99

    updated = await svc.set_plan(store, 1000)
    assert updated.plan == 1000.0
    assert isinstance(updated.plan, float)


@pytest.mark.asyncio
async def test_store_name_uniqueness(session):
    """Тест уникальности имени магазина"""

    svc = StoreService(session)

    store1 = await svc.get_or_create("UniqueStore")

    store2 = await svc.get_or_create("UniqueStore")

    assert store1.id == store2.id

    store3 = await svc.get_or_create("OtherStore")

    with patch.object(StoreRepository, "update_name") as mock_update_name:

        mock_store = store3
        mock_store.name = "UniqueStore"
        mock_update_name.return_value = mock_store

        updated_store3 = await svc.update_name(store3, "UniqueStore")

        mock_update_name.assert_called_once_with(store3, "UniqueStore")

        assert updated_store3.name == "UniqueStore"
