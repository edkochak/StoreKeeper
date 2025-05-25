import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.middleware import UpdateChatIdMiddleware
from app.models.user import User


class TestMiddlewareScenarios:
    """Тесты сценариев использования middleware"""

    @pytest.mark.asyncio
    async def test_admin_changing_device_scenario(self):
        """Сценарий: Администратор переходит на новое устройство с другим chat_id"""
        middleware = UpdateChatIdMiddleware()

        admin_user = User()
        admin_user.id = 1
        admin_user.first_name = "admin1"
        admin_user.last_name = "Admin"
        admin_user.role = "admin"
        admin_user.chat_id = 111111111

        message = AsyncMock()
        message.chat.id = 999999999

        state = AsyncMock()
        state.get_data.return_value = {
            "user_id": 1,
            "first_name": "admin1",
            "last_name": "Admin",
            "role": "admin",
        }

        handler = AsyncMock()
        handler.return_value = "Command executed"

        data = {"state": state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_by_id.return_value = admin_user

                async def update_chat_id_mock(user, new_chat_id):
                    user.chat_id = new_chat_id
                    return user

                mock_service.update_chat_id.side_effect = update_chat_id_mock

                result = await middleware(handler, message, data)

                assert result == "Command executed"
                mock_service.get_by_id.assert_called_once_with(1)
                mock_service.update_chat_id.assert_called_once_with(
                    admin_user, 999999999
                )
                handler.assert_called_once_with(message, data)

                assert admin_user.chat_id == 999999999

    @pytest.mark.asyncio
    async def test_subscriber_authentication_scenario(self):
        """Сценарий: Подписчик авторизуется впервые"""
        middleware = UpdateChatIdMiddleware()

        subscriber_user = User()
        subscriber_user.id = 5
        subscriber_user.first_name = "Subscriber"
        subscriber_user.last_name = "555666777"
        subscriber_user.role = "subscriber"
        subscriber_user.chat_id = 555666777

        message = AsyncMock()
        message.chat.id = 555666777

        state = AsyncMock()
        state.get_data.return_value = {
            "user_id": 5,
            "first_name": "Subscriber",
            "last_name": "555666777",
            "role": "subscriber",
        }

        handler = AsyncMock()
        handler.return_value = "Subscriber command processed"

        data = {"state": state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_by_id.return_value = subscriber_user

                result = await middleware(handler, message, data)

                assert result == "Subscriber command processed"
                mock_service.get_by_id.assert_called_once_with(5)

                mock_service.update_chat_id.assert_not_called()
                handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_manager_switching_accounts_scenario(self):
        """Сценарий: Менеджер переключается между аккаунтами на одном устройстве"""
        middleware = UpdateChatIdMiddleware()

        manager1 = User()
        manager1.id = 2
        manager1.first_name = "Manager1"
        manager1.last_name = "Store1"
        manager1.role = "manager"
        manager1.chat_id = 777888999

        manager2 = User()
        manager2.id = 3
        manager2.first_name = "Manager2"
        manager2.last_name = "Store2"
        manager2.role = "manager"
        manager2.chat_id = 111222333

        message = AsyncMock()
        message.chat.id = 777888999

        handler = AsyncMock()
        handler.return_value = "Manager command processed"

        state1 = AsyncMock()
        state1.get_data.return_value = {
            "user_id": 2,
            "first_name": "Manager1",
            "last_name": "Store1",
            "role": "manager",
        }

        data1 = {"state": state1}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_by_id.return_value = manager1

                result1 = await middleware(handler, message, data1)

                assert result1 == "Manager command processed"
                mock_service.update_chat_id.assert_not_called()

        state2 = AsyncMock()
        state2.get_data.return_value = {
            "user_id": 3,
            "first_name": "Manager2",
            "last_name": "Store2",
            "role": "manager",
        }

        data2 = {"state": state2}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_by_id.return_value = manager2

                async def update_chat_id_mock(user, new_chat_id):
                    user.chat_id = new_chat_id
                    return user

                mock_service.update_chat_id.side_effect = update_chat_id_mock

                result2 = await middleware(handler, message, data2)

                assert result2 == "Manager command processed"
                mock_service.update_chat_id.assert_called_once_with(manager2, 777888999)
                assert manager2.chat_id == 777888999

    @pytest.mark.asyncio
    async def test_unauthenticated_user_scenario(self):
        """Сценарий: Неавторизованный пользователь отправляет команду"""
        middleware = UpdateChatIdMiddleware()

        message = AsyncMock()
        message.chat.id = 123456789

        state = AsyncMock()
        state.get_data.return_value = {}

        handler = AsyncMock()
        handler.return_value = "Please authenticate first"

        data = {"state": state}

        with patch("app.middleware.get_session") as mock_get_session:
            with patch("app.middleware.UserService") as mock_user_service:

                result = await middleware(handler, message, data)

                assert result == "Please authenticate first"

                mock_get_session.assert_not_called()
                mock_user_service.assert_not_called()
                handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_deleted_user_scenario(self):
        """Сценарий: Пользователь был удален из системы, но состояние сохранилось"""
        middleware = UpdateChatIdMiddleware()

        message = AsyncMock()
        message.chat.id = 123456789

        state = AsyncMock()
        state.get_data.return_value = {
            "user_id": 999,
            "first_name": "Deleted",
            "last_name": "User",
            "role": "manager",
        }

        handler = AsyncMock()
        handler.return_value = "User not found, please re-authenticate"

        data = {"state": state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service = AsyncMock()
                mock_user_service.return_value = mock_service
                mock_service.get_by_id.return_value = None

                result = await middleware(handler, message, data)

                assert result == "User not found, please re-authenticate"
                mock_service.get_by_id.assert_called_once_with(999)
                mock_service.update_chat_id.assert_not_called()
                handler.assert_called_once_with(message, data)
