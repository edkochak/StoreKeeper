import pytest
import asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_store_service_error_handling(session):
    """Тест обработки ошибок в сервисе магазинов"""
    
    # Создаем сервис с реальной сессией
    svc = StoreService(session)
    
    # Патчим метод репозитория, чтобы он бросал исключение
    with patch.object(StoreRepository, 'update_name', side_effect=SQLAlchemyError("DB Error")):
        # Создаем тестовый магазин
        store = await svc.get_or_create("ErrorTest")
        
        # Попытка обновить магазин должна перехватить исключение
        with pytest.raises(SQLAlchemyError):
            await svc.update_name(store, "NewName")


@pytest.mark.asyncio
async def test_user_service_error_handling(session):
    """Тест обработки ошибок в сервисе пользователей"""
    
    # Создаем сервис с реальной сессией
    svc = UserService(session)
    
    # Патчим метод репозитория, чтобы он бросал исключение
    with patch.object(UserRepository, 'update_first_name', side_effect=SQLAlchemyError("DB Error")):
        # Создаем тестового пользователя
        user = await svc.get_or_create("ErrorTest", "User", "manager")
        
        # Попытка обновить пользователя должна перехватить исключение
        with pytest.raises(SQLAlchemyError):
            await svc.update_first_name(user, "NewName")


@pytest.mark.asyncio
async def test_retry_logic(session):
    """Тест логики повторных попыток при временных ошибках"""
    
    # Создаем счетчик вызовов
    call_count = 0
    
    # Мок-функция, которая сначала бросает исключение, потом работает нормально
    async def mock_update(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:  # первые два вызова бросают исключение
            raise SQLAlchemyError("Temporary error")
        return args[0]  # возвращаем первый аргумент (объект)
    
    # Патчим метод в репозитории
    with patch.object(StoreRepository, 'update_name', side_effect=mock_update):
        svc = StoreService(session)
        store = await svc.get_or_create("RetryTest")
        
        # Добавляем логику повторных попыток в сервис
        async def retry_update(store, name, max_attempts=3):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await svc.update_name(store, name)
                except SQLAlchemyError as e:
                    if attempt == max_attempts:
                        raise
                    await asyncio.sleep(0.1)  # небольшая задержка перед повторной попыткой
        
        # Проверяем, что функция с retry выполнилась успешно
        result = await retry_update(store, "RetrySuccess")
        
        # Должно быть 3 вызова: 2 с ошибками и 1 успешный
        assert call_count == 3
        assert result is store  # возвращается тот же объект
