import pytest
from app.services.user_service import UserService
from app.services.store_service import StoreService
from app.models.user import User


@pytest.mark.asyncio
async def test_user_update_first_name(session):
    """Тест обновления имени пользователя"""
    # Инициализация сервиса
    svc = UserService(session)
    
    # Создаем тестового пользователя
    user = await svc.get_or_create("TestFirst", "TestLast", "manager")
    assert isinstance(user, User)
    assert user.first_name == "TestFirst"
    
    # Обновляем имя
    updated_user = await svc.update_first_name(user, "UpdatedFirst")
    assert updated_user.id == user.id
    assert updated_user.first_name == "UpdatedFirst"
    assert updated_user.last_name == "TestLast"  # Фамилия не меняется
    
    # Проверяем, что изменения сохранились
    user_from_db = await svc.get_by_name("UpdatedFirst", "TestLast")
    assert user_from_db is not None
    assert user_from_db.first_name == "UpdatedFirst"


@pytest.mark.asyncio
async def test_user_update_last_name(session):
    """Тест обновления фамилии пользователя"""
    # Инициализация сервиса
    svc = UserService(session)
    
    # Создаем тестового пользователя
    user = await svc.get_or_create("LastTest", "OriginalLast", "manager")
    assert user.last_name == "OriginalLast"
    
    # Обновляем фамилию
    updated_user = await svc.update_last_name(user, "UpdatedLast")
    assert updated_user.id == user.id
    assert updated_user.first_name == "LastTest"  # Имя не меняется
    assert updated_user.last_name == "UpdatedLast"
    
    # Проверяем, что изменения сохранились
    user_from_db = await svc.get_by_name("LastTest", "UpdatedLast")
    assert user_from_db is not None
    assert user_from_db.last_name == "UpdatedLast"


@pytest.mark.asyncio
async def test_user_assign_store(session):
    """Тест привязки пользователя к магазину и отвязки"""
    # Инициализация сервисов
    user_svc = UserService(session)
    store_svc = StoreService(session)
    
    # Создаем тестового пользователя без привязки к магазину
    user = await user_svc.get_or_create("StoreAssign", "Test", "manager")
    assert user.store_id is None
    
    # Создаем магазин
    store = await store_svc.get_or_create("AssignTestStore")
    
    # Привязываем пользователя к магазину
    updated_user = await user_svc.assign_store(user, store.id)
    assert updated_user.store_id == store.id
    
    # Проверяем связь в базе
    user_from_db = await user_svc.get_by_name("StoreAssign", "Test")
    assert user_from_db.store_id == store.id
    assert user_from_db.store.name == "AssignTestStore"
    
    # Отвязываем пользователя от магазина (store_id = None)
    unassigned_user = await user_svc.assign_store(user_from_db, None)
    assert unassigned_user.store_id is None
    
    # Проверяем отвязку в базе
    final_user = await user_svc.get_by_name("StoreAssign", "Test")
    assert final_user.store_id is None


@pytest.mark.asyncio
async def test_user_update_with_multiple_users(session):
    """Тест обновления пользователей при наличии нескольких пользователей в базе"""
    # Инициализация сервиса
    svc = UserService(session)
    
    # Создаем несколько пользователей
    user1 = await svc.get_or_create("Multi1", "Test", "manager")
    user2 = await svc.get_or_create("Multi2", "Test", "manager")
    user3 = await svc.get_or_create("Multi3", "Test", "manager")
    
    # Обновляем имя второго пользователя
    updated_user2 = await svc.update_first_name(user2, "MultiUpdated")
    
    # Проверяем, что обновился только нужный пользователь
    all_users = await svc.get_all_users()
    assert len(all_users) >= 3  # может быть больше из-за других тестов
    
    # Ищем наших пользователей в списке
    updated_user_found = False
    original_users_found = 0
    
    for user in all_users:
        if user.first_name == "MultiUpdated" and user.last_name == "Test":
            updated_user_found = True
            assert user.id == user2.id
        elif user.first_name in ["Multi1", "Multi3"] and user.last_name == "Test":
            original_users_found += 1
    
    assert updated_user_found
    assert original_users_found == 2
