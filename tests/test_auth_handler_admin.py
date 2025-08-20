import pytest
from unittest.mock import patch, AsyncMock
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.auth_handler import cmd_start, process_name
from app.core.states import AuthStates
from app.services.user_service import UserService


@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=111, from_user_id=111):
        message = AsyncMock(spec=Message)
        message.text = text
        message.chat = Chat(id=chat_id, type="private")
        message.from_user = TgUser(id=from_user_id, is_bot=False, first_name="Test")
        message.answer = AsyncMock()
        return message

    return _create_message


@pytest.fixture
def state():
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key="test")
    return state


@pytest.mark.asyncio
async def test_admin_start_auto_create(session, create_message, state):
    # Подменяем список администраторов и сессию
    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.handlers.auth_handler.ADMIN_CHAT_IDS", [111]):
        with patch("app.handlers.auth_handler.get_session", return_value=SessionContext()):
            msg = create_message(chat_id=111)
            await cmd_start(msg, state)

    # Проверяем, что создан пользователь admin1 Admin с ролью admin
    user_svc = UserService(session)
    user = await user_svc.get_by_name("admin1", "Admin")
    assert user is not None
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_process_name_unknown_user_rejected(session, create_message, state):
    msg = create_message(text="Unknown User", chat_id=222)

    await state.set_state(AuthStates.waiting_name)

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.handlers.auth_handler.get_session", return_value=SessionContext()):
        await process_name(msg, state)

    # Ожидаем сообщение о неуспешной авторизации и очистку состояния
    msg.answer.assert_awaited()
    assert await state.get_state() is None
