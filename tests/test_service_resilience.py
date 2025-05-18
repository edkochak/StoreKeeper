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

    svc = StoreService(session)

    with patch.object(
        StoreRepository, "update_name", side_effect=SQLAlchemyError("DB Error")
    ):

        store = await svc.get_or_create("ErrorTest")

        with pytest.raises(SQLAlchemyError):
            await svc.update_name(store, "NewName")


@pytest.mark.asyncio
async def test_user_service_error_handling(session):
    """Тест обработки ошибок в сервисе пользователей"""

    svc = UserService(session)

    with patch.object(
        UserRepository, "update_first_name", side_effect=SQLAlchemyError("DB Error")
    ):

        user = await svc.get_or_create("ErrorTest", "User", "manager")

        with pytest.raises(SQLAlchemyError):
            await svc.update_first_name(user, "NewName")


@pytest.mark.asyncio
async def test_retry_logic(session):
    """Тест логики повторных попыток при временных ошибках"""

    call_count = 0

    async def mock_update(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise SQLAlchemyError("Temporary error")
        return args[0]

    with patch.object(StoreRepository, "update_name", side_effect=mock_update):
        svc = StoreService(session)
        store = await svc.get_or_create("RetryTest")

        async def retry_update(store, name, max_attempts=3):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await svc.update_name(store, name)
                except SQLAlchemyError as e:
                    if attempt == max_attempts:
                        raise
                    await asyncio.sleep(0.1)

        result = await retry_update(store, "RetrySuccess")

        assert call_count == 3
        assert result is store
