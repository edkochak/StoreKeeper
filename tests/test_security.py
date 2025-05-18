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
    # Патчим ADMIN_CHAT_IDS для тестов
    original_ids = ADMIN_CHAT_IDS[:]
    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend([987654321])
    yield ADMIN_CHAT_IDS
    # Восстанавливаем оригинальные значения
    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend(original_ids)


@pytest.mark.asyncio
async def test_admin_commands_access_denied(create_message, state, admin_chat_ids):
    """Тест запрета доступа к админским командам для неадминистраторов"""
    # Создаем сообщение от обычного пользователя (не админа)
    message = create_message(chat_id=123456789)  # ID не входит в admin_chat_ids
    
    # Пытаемся использовать админские команды
    await cmd_report(message, state)
    message.answer.assert_called_once()
    assert "нет прав администратора" in message.answer.call_args[0][0].lower()
    
    # Сбрасываем мок
    message.answer.reset_mock()
    
    # Пробуем другую админскую команду
    await cmd_add_store(message, state)
    message.answer.assert_called_once()
    assert "нет прав администратора" in message.answer.call_args[0][0].lower()
    
    # Сбрасываем мок
    message.answer.reset_mock()
    
    # Пробуем третью админскую команду
    await cmd_add_manager(message, state)
    message.answer.assert_called_once()
    assert "нет прав администратора" in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_admin_commands_access_granted(create_message, state, admin_chat_ids):
    """Тест разрешения доступа к админским командам для администраторов"""
    # Создаем сообщение от администратора
    message = create_message(chat_id=987654321)  # ID входит в admin_chat_ids
    
    # Патчим внутренние методы, чтобы тест не пытался работать с реальными данными
    with patch('app.handlers.admin_handler.get_session'):
        with patch('app.handlers.admin_handler.StoreService'):
            # Пытаемся использовать админскую команду
            await cmd_add_store(message, state)
            
            # Проверяем, что сообщение отправлено и это не отказ в доступе
            message.answer.assert_called_once()
            assert "нет прав администратора" not in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_user_role_permissions(session):
    """Тест проверки разрешений на основе ролей пользователей"""
    # Создаем сервис
    user_service = UserService(session)
    
    # Создаем тестовых пользователей с разными ролями
    admin = await user_service.get_or_create("Test", "Admin", "admin")
    manager = await user_service.get_or_create("Test", "Manager", "manager")
    
    # Проверяем разрешения
    assert user_service.can_view_reports(admin)
    assert user_service.can_manage_stores(admin)
    assert user_service.can_manage_users(admin)
    
    assert not user_service.can_view_reports(manager)
    assert not user_service.can_manage_stores(manager)
    assert not user_service.can_manage_users(manager)
