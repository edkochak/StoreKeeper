import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.middleware import UpdateChatIdMiddleware
from app.models.user import User


class TestUpdateChatIdMiddleware:
    """Тесты для middleware UpdateChatIdMiddleware"""

    @pytest.fixture
    def middleware(self):
        """Создание экземпляра middleware"""
        return UpdateChatIdMiddleware()

    @pytest.fixture
    def mock_handler(self):
        """Мок-обработчик"""
        handler = AsyncMock()
        handler.return_value = "handler_result"
        return handler

    @pytest.fixture
    def mock_message(self):
        """Мок-сообщение"""
        message = MagicMock()
        message.chat.id = 123456789
        return message

    @pytest.fixture
    def mock_state(self):
        """Мок состояния FSM"""
        state = AsyncMock()
        return state

    @pytest.fixture
    def mock_user(self):
        """Мок пользователя"""
        user = User()
        user.id = 1
        user.first_name = "TestUser"
        user.last_name = "TestLastName"
        user.chat_id = 987654321
        user.role = "manager"
        return user

    @pytest.mark.asyncio
    async def test_middleware_updates_chat_id_when_different(
        self, middleware, mock_handler, mock_message, mock_state, mock_user
    ):
        """Тест обновления chat_id когда он отличается"""

        mock_state.get_data.return_value = {"user_id": 1}

        data = {"state": mock_state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service_instance = AsyncMock()
                mock_user_service.return_value = mock_service_instance
                mock_service_instance.get_by_id.return_value = mock_user
                mock_service_instance.update_chat_id.return_value = mock_user

                result = await middleware(mock_handler, mock_message, data)

                assert result == "handler_result"
                mock_state.get_data.assert_called_once()
                mock_service_instance.get_by_id.assert_called_once_with(1)
                mock_service_instance.update_chat_id.assert_called_once_with(
                    mock_user, 123456789
                )
                mock_handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_skips_when_chat_id_same(
        self, middleware, mock_handler, mock_message, mock_state, mock_user
    ):
        """Тест пропуска обновления когда chat_id не изменился"""

        mock_user.chat_id = 123456789
        mock_state.get_data.return_value = {"user_id": 1}

        data = {"state": mock_state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service_instance = AsyncMock()
                mock_user_service.return_value = mock_service_instance
                mock_service_instance.get_by_id.return_value = mock_user

                result = await middleware(mock_handler, mock_message, data)

                assert result == "handler_result"
                mock_state.get_data.assert_called_once()
                mock_service_instance.get_by_id.assert_called_once_with(1)

                mock_service_instance.update_chat_id.assert_not_called()
                mock_handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_skips_when_no_user_id(
        self, middleware, mock_handler, mock_message, mock_state
    ):
        """Тест пропуска обновления когда пользователь не авторизован"""

        mock_state.get_data.return_value = {}

        data = {"state": mock_state}

        with patch("app.middleware.get_session") as mock_get_session:
            with patch("app.middleware.UserService") as mock_user_service:

                result = await middleware(mock_handler, mock_message, data)

                assert result == "handler_result"
                mock_state.get_data.assert_called_once()

                mock_get_session.assert_not_called()
                mock_user_service.assert_not_called()
                mock_handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_skips_when_no_state(
        self, middleware, mock_handler, mock_message
    ):
        """Тест пропуска обновления когда нет состояния FSM"""

        data = {}

        with patch("app.middleware.get_session") as mock_get_session:
            with patch("app.middleware.UserService") as mock_user_service:

                result = await middleware(mock_handler, mock_message, data)

                assert result == "handler_result"

                mock_get_session.assert_not_called()
                mock_user_service.assert_not_called()
                mock_handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_skips_when_user_not_found(
        self, middleware, mock_handler, mock_message, mock_state
    ):
        """Тест пропуска обновления когда пользователь не найден в БД"""

        mock_state.get_data.return_value = {"user_id": 999}

        data = {"state": mock_state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch("app.middleware.UserService") as mock_user_service:
                mock_service_instance = AsyncMock()
                mock_user_service.return_value = mock_service_instance
                mock_service_instance.get_by_id.return_value = None

                result = await middleware(mock_handler, mock_message, data)

                assert result == "handler_result"
                mock_state.get_data.assert_called_once()
                mock_service_instance.get_by_id.assert_called_once_with(999)

                mock_service_instance.update_chat_id.assert_not_called()
                mock_handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_handles_database_error(
        self, middleware, mock_handler, mock_message, mock_state, caplog
    ):
        """Тест обработки ошибки базы данных"""

        mock_state.get_data.return_value = {"user_id": 1}

        data = {"state": mock_state}

        with caplog.at_level("ERROR", logger="app.middleware"):
            with patch("app.middleware.get_session") as mock_get_session:

                mock_get_session.side_effect = Exception("Database connection error")

                result = await middleware(mock_handler, mock_message, data)

                assert result == "handler_result"
                mock_state.get_data.assert_called_once()

                mock_handler.assert_called_once_with(mock_message, data)

                assert "Ошибка при обновлении chat_id" in caplog.text

    @pytest.mark.asyncio
    async def test_middleware_handles_user_service_error(
        self, middleware, mock_handler, mock_message, mock_state, mock_user, caplog
    ):
        """Тест обработки ошибки в UserService"""

        mock_state.get_data.return_value = {"user_id": 1}

        data = {"state": mock_state}

        with caplog.at_level("ERROR", logger="app.middleware"):
            with patch("app.middleware.get_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session

                with patch("app.middleware.UserService") as mock_user_service:
                    mock_service_instance = AsyncMock()
                    mock_user_service.return_value = mock_service_instance
                    mock_service_instance.get_by_id.return_value = mock_user

                    mock_service_instance.update_chat_id.side_effect = Exception(
                        "Update error"
                    )

                    result = await middleware(mock_handler, mock_message, data)

                    assert result == "handler_result"
                    mock_state.get_data.assert_called_once()
                    mock_service_instance.get_by_id.assert_called_once_with(1)
                    mock_service_instance.update_chat_id.assert_called_once_with(
                        mock_user, 123456789
                    )

                    mock_handler.assert_called_once_with(mock_message, data)

                    assert "Ошибка при обновлении chat_id" in caplog.text

    @pytest.mark.asyncio
    async def test_middleware_logs_successful_update(
        self, middleware, mock_handler, mock_message, mock_state, mock_user, caplog
    ):
        """Тест логирования успешного обновления"""

        mock_state.get_data.return_value = {"user_id": 1}

        data = {"state": mock_state}

        with caplog.at_level("INFO", logger="app.middleware"):
            with patch("app.middleware.get_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session

                with patch("app.middleware.UserService") as mock_user_service:
                    mock_service_instance = AsyncMock()
                    mock_user_service.return_value = mock_service_instance
                    mock_service_instance.get_by_id.return_value = mock_user
                    mock_service_instance.update_chat_id.return_value = mock_user

                    result = await middleware(mock_handler, mock_message, data)

                    assert result == "handler_result"

                    assert (
                        "Chat ID обновлен для пользователя TestUser TestLastName"
                        in caplog.text
                    )

    @pytest.mark.asyncio
    async def test_middleware_preserves_handler_result(
        self, middleware, mock_handler, mock_message, mock_state
    ):
        """Тест сохранения результата обработчика"""

        mock_state.get_data.return_value = {}
        expected_result = {"status": "success", "data": [1, 2, 3]}
        mock_handler.return_value = expected_result

        data = {"state": mock_state}

        result = await middleware(mock_handler, mock_message, data)

        assert result == expected_result
        mock_handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_preserves_handler_exception(
        self, middleware, mock_handler, mock_message, mock_state
    ):
        """Тест сохранения исключений от обработчика"""

        mock_state.get_data.return_value = {}
        expected_exception = ValueError("Handler error")
        mock_handler.side_effect = expected_exception

        data = {"state": mock_state}

        with pytest.raises(ValueError, match="Handler error"):
            await middleware(mock_handler, mock_message, data)

        mock_handler.assert_called_once_with(mock_message, data)
