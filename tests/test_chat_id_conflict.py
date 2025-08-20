import pytest
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_chat_id_unique_conflict_resolved(session):
    user_svc = UserService(session)

    # Создаём двух пользователей без chat_id
    u1 = await user_svc.get_or_create("Alice", "One", "manager")
    u2 = await user_svc.get_or_create("Bob", "Two", "manager")

    # Назначаем chat_id первому
    await user_svc.update_chat_id(u1, 999)

    # Назначаем тот же chat_id второму — должен освобождаться у первого и переходить ко второму
    await user_svc.update_chat_id(u2, 999)

    # Обновляем объекты из БД
    u1_loaded = await user_svc.get_by_name("Alice", "One")
    u2_loaded = await user_svc.get_by_name("Bob", "Two")

    assert u1_loaded.chat_id is None
    assert u2_loaded.chat_id == 999
