import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.admin_handler import cmd_report, cmd_add_store, cmd_add_manager
from app.core.config import ADMIN_CHAT_IDS
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
def admin_chat_ids():

    original_ids = ADMIN_CHAT_IDS[:]
    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend([987654321])
    yield ADMIN_CHAT_IDS

    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend(original_ids)


@pytest.mark.asyncio
async def test_admin_commands_access_denied(create_message, state, admin_chat_ids):
    """Тест запрета доступа к админским командам для неадминистраторов"""

    message = create_message(chat_id=123456789)

    await cmd_report(message, state)
    message.answer.assert_called_once()
    assert "нет прав администратора" in message.answer.call_args[0][0].lower()

    message.answer.reset_mock()

    await cmd_add_store(message, state)
    message.answer.assert_called_once()
    assert "нет прав администратора" in message.answer.call_args[0][0].lower()

    message.answer.reset_mock()

    await cmd_add_manager(message, state)
    message.answer.assert_called_once()
    assert "нет прав администратора" in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_admin_commands_access_granted_env(create_message, state, admin_chat_ids):
    """Доступ к админ-командам по ADMIN_CHAT_IDS (из .env)"""

    message = create_message(chat_id=987654321)

    with patch("app.handlers.admin_handler.get_session"), \
        patch("app.utils.permissions.get_session"):
        with patch("app.handlers.admin_handler.StoreService"):
            await cmd_add_store(message, state)
            message.answer.assert_called_once()
            assert (
                "нет прав администратора" not in message.answer.call_args[0][0].lower()
            )


@pytest.mark.asyncio
async def test_admin_commands_access_granted_db_role(create_message, state, session):
    """Доступ к админ-командам по роли admin в БД (без наличия в .env)"""

    # Создаём пользователя с ролью admin и chat_id
    from app.services.user_service import UserService

    user_svc = UserService(session)
    user = await user_svc.get_or_create("Db", "Admin", "admin")
    await user_svc.update_chat_id(user, 555777)

    message = create_message(chat_id=555777)

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.handlers.admin_handler.get_session", return_value=SessionContext()), \
        patch("app.utils.permissions.get_session", return_value=SessionContext()):
        with patch("app.handlers.admin_handler.StoreService"):
            await cmd_add_store(message, state)
            message.answer.assert_called_once()
            assert (
                "нет прав администратора" not in message.answer.call_args[0][0].lower()
            )


@pytest.mark.asyncio
async def test_user_role_permissions(session):
    """Тест проверки разрешений на основе ролей пользователей"""

    user_service = UserService(session)

    admin = await user_service.get_or_create("Test", "Admin", "admin")
    manager = await user_service.get_or_create("Test", "Manager", "manager")

    assert user_service.can_view_reports(admin)
    assert user_service.can_manage_stores(admin)
    assert user_service.can_manage_users(admin)

    assert not user_service.can_view_reports(manager)
    assert not user_service.can_manage_stores(manager)
    assert not user_service.can_manage_users(manager)
