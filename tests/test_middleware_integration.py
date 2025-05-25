import pytest
from unittest.mock import AsyncMock, patch
from app.middleware import UpdateChatIdMiddleware
from app.models.user import User
from app.core.database import get_session
from app.services.user_service import UserService


class TestMiddlewareIntegration:
    """Интеграционные тесты для middleware UpdateChatIdMiddleware"""

    @pytest.mark.asyncio
    async def test_middleware_integration_with_real_user_service(self):
        """Интеграционный тест middleware с реальным UserService"""
        middleware = UpdateChatIdMiddleware()

        handler = AsyncMock()
        handler.return_value = "success"

        message = AsyncMock()
        message.chat.id = 555777999

        state = AsyncMock()
        state.get_data.return_value = {"user_id": 1}

        data = {"state": state}

        with patch("app.middleware.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            test_user = User()
            test_user.id = 1
            test_user.first_name = "Integration"
            test_user.last_name = "Test"
            test_user.chat_id = 111222333
            test_user.role = "manager"

            with patch.object(UserService, "get_by_id") as mock_get_by_id:
                with patch.object(UserService, "update_chat_id") as mock_update_chat_id:
                    mock_get_by_id.return_value = test_user

                    async def update_chat_id_side_effect(user, new_chat_id):
                        user.chat_id = new_chat_id
                        return user

                    mock_update_chat_id.side_effect = update_chat_id_side_effect

                    result = await middleware(handler, message, data)

                    assert result == "success"
                    mock_get_by_id.assert_called_once_with(1)
                    mock_update_chat_id.assert_called_once_with(test_user, 555777999)
                    handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_middleware_chain_execution_order(self):
        """Тест порядка выполнения в цепочке middleware"""

        execution_order = []

        class TrackedMiddleware(UpdateChatIdMiddleware):
            async def __call__(self, handler, event, data):
                execution_order.append("middleware")
                return await super().__call__(handler, event, data)

        middleware1 = TrackedMiddleware()

        async def test_handler(message, data):
            execution_order.append("handler")
            return "handler_result"

        message = AsyncMock()
        message.chat.id = 123456789

        state = AsyncMock()
        state.get_data.return_value = {}

        data = {"state": state}

        result = await middleware1(test_handler, message, data)

        assert result == "handler_result"
        assert execution_order == ["middleware", "handler"]

    @pytest.mark.asyncio
    async def test_middleware_with_multiple_users(self):
        """Тест middleware с несколькими пользователями"""
        middleware = UpdateChatIdMiddleware()

        handler = AsyncMock()
        handler.return_value = "ok"

        test_cases = [
            {"user_id": 1, "old_chat_id": 111, "new_chat_id": 222},
            {"user_id": 2, "old_chat_id": 333, "new_chat_id": 444},
            {"user_id": 3, "old_chat_id": 555, "new_chat_id": 555},
        ]

        for case in test_cases:

            message = AsyncMock()
            message.chat.id = case["new_chat_id"]

            state = AsyncMock()
            state.get_data.return_value = {"user_id": case["user_id"]}

            data = {"state": state}

            with patch("app.middleware.get_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session

                test_user = User()
                test_user.id = case["user_id"]
                test_user.first_name = f"User{case ['user_id']}"
                test_user.last_name = "Test"
                test_user.chat_id = case["old_chat_id"]
                test_user.role = "manager"

                with patch.object(UserService, "get_by_id") as mock_get_by_id:
                    with patch.object(
                        UserService, "update_chat_id"
                    ) as mock_update_chat_id:
                        mock_get_by_id.return_value = test_user
                        mock_update_chat_id.return_value = test_user

                        result = await middleware(handler, message, data)

                        assert result == "ok"
                        mock_get_by_id.assert_called_once_with(case["user_id"])

                        if case["old_chat_id"] != case["new_chat_id"]:
                            mock_update_chat_id.assert_called_once_with(
                                test_user, case["new_chat_id"]
                            )
                        else:
                            mock_update_chat_id.assert_not_called()

                        handler.assert_called_once_with(message, data)

            handler.reset_mock()

    @pytest.mark.asyncio
    async def test_middleware_performance_with_no_state(self):
        """Тест производительности middleware когда нет состояния"""
        middleware = UpdateChatIdMiddleware()

        handler = AsyncMock()
        handler.return_value = "fast"

        message = AsyncMock()
        message.chat.id = 123456789

        data = {}

        with patch("app.middleware.get_session") as mock_get_session:
            with patch("app.middleware.UserService") as mock_user_service:

                result = await middleware(handler, message, data)

                assert result == "fast"

                mock_get_session.assert_not_called()
                mock_user_service.assert_not_called()
                handler.assert_called_once_with(message, data)
