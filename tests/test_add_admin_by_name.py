import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.admin_handler import (
    cmd_add_admin,
    process_add_admin_full_name,
)
from app.core.states import AdminManagementStates
from app.services.user_service import UserService


@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=123456789, from_user_id=123456789):
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


@pytest.fixture
def session_patch(session):
    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.handlers.admin_handler.get_session", return_value=SessionContext()):
        yield session


@pytest.mark.asyncio
async def test_add_admin_creates_new_user(create_message, state, session_patch):
    with patch("app.handlers.admin_handler.ADMIN_CHAT_IDS", [987654321]), \
         patch("app.utils.permissions.ADMIN_CHAT_IDS", [987654321]), \
         patch("app.utils.permissions.get_session", return_value=type("S", (), {"__aenter__": lambda s: session_patch, "__aexit__": lambda s, *a: None})()):
        # Старт команды от администратора
        msg = create_message(chat_id=987654321)
        await cmd_add_admin(msg, state)

        msg.answer.assert_called_once()
        assert await state.get_state() == AdminManagementStates.waiting_full_name

        # Ввод ФИО несуществующего пользователя
        input_msg = create_message("Alice Smith", chat_id=987654321)
        await process_add_admin_full_name(input_msg, state)

        # Проверяем, что пользователь создан и имеет роль admin
        user_svc = UserService(session_patch)
        user = await user_svc.get_by_name("Alice", "Smith")
        assert user is not None
        assert user.role == "admin"
        assert await state.get_state() is None


@pytest.mark.asyncio
async def test_add_admin_promotes_existing_user(create_message, state, session_patch):
    user_svc = UserService(session_patch)
    existing = await user_svc.get_or_create("Bob", "Jones", "manager")
    assert existing.role == "manager"

    with patch("app.handlers.admin_handler.ADMIN_CHAT_IDS", [987654321]), \
         patch("app.utils.permissions.ADMIN_CHAT_IDS", [987654321]), \
         patch("app.utils.permissions.get_session", return_value=type("S", (), {"__aenter__": lambda s: session_patch, "__aexit__": lambda s, *a: None})()):
        msg = create_message(chat_id=987654321)
        await cmd_add_admin(msg, state)

        input_msg = create_message("Bob Jones", chat_id=987654321)
        await process_add_admin_full_name(input_msg, state)

        updated = await user_svc.get_by_name("Bob", "Jones")
        assert updated.role == "admin"


@pytest.mark.asyncio
async def test_add_admin_denied_for_non_admin(create_message, state):
    # Пользователь не в списке ADMIN_CHAT_IDS
    msg = create_message(chat_id=111)
    await cmd_add_admin(msg, state)
    msg.answer.assert_called_once()
    assert "нет прав администратора" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_add_admin_invalid_full_name(create_message, state, session_patch):
    with patch("app.handlers.admin_handler.ADMIN_CHAT_IDS", [987654321]), \
         patch("app.utils.permissions.ADMIN_CHAT_IDS", [987654321]), \
         patch("app.utils.permissions.get_session", return_value=type("S", (), {"__aenter__": lambda s: session_patch, "__aexit__": lambda s, *a: None})()):
        msg = create_message(chat_id=987654321)
        await cmd_add_admin(msg, state)

        # Имя/фамилия с пробелами в каждой части должны быть отклонены бизнес-логикой
        input_msg = create_message("John Paul Van Doe", chat_id=987654321)
        await process_add_admin_full_name(input_msg, state)

        # Остаёмся в состоянии ожидания корректного ввода
        assert await state.get_state() == AdminManagementStates.waiting_full_name
