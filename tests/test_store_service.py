import pytest
from app.services.store_service import StoreService
from app.models.store import Store


@pytest.mark.asyncio
async def test_store_service(session):
    svc = StoreService(session)

    stores = await svc.list_stores()
    assert stores == []

    store = await svc.get_or_create("TestStore")
    assert isinstance(store, Store)
    assert store.id is not None
    assert store.name == "TestStore"

    same_store = await svc.get_or_create("TestStore")
    assert same_store.id == store.id

    stores = await svc.list_stores()
    assert len(stores) == 1
    assert stores[0].name == "TestStore"


@pytest.mark.asyncio
async def test_set_plan(session):
    svc = StoreService(session)

    store = await svc.get_or_create("PlanStore")
    updated = await svc.set_plan(store, 250.5)
    assert updated.plan == 250.5

    stores = await svc.list_stores()
    assert len(stores) == 1
    assert stores[0].plan == 250.5
