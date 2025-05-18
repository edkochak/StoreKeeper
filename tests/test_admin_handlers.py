import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.handlers.admin_handler import (cmd_edit_store, process_edit_store_selection, 
                                       process_edit_store_field, process_edit_store_value,
                                       cmd_edit_manager, process_edit_manager_selection,
                                       process_edit_manager_field, process_edit_manager_value)
from app.core.states import EditStoreStates, EditManagerStates
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.models.store import Store
from app.models.user import User


# Фикстура для создания фейкового сообщения
@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=329008489, from_user_id=329008489):
        message = AsyncMock(spec=Message)
        message.text = text
        message.chat = Chat(id=chat_id, type="private")
        message.from_user = TgUser(id=from_user_id, is_bot=False, first_name="Test")
        # Правильная настройка метода answer для AsyncMock
        message.answer = AsyncMock()
        message.answer.return_value = AsyncMock()
        return message
    return _create_message


# Фикстура для создания контекста состояния
@pytest.fixture
def state():
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key="test")
    return state


# Патч для get_session
@pytest.fixture
def session_patch(session):
    # Создаем контекстный менеджер, который просто возвращает сессию
    class SessionContext:
        async def __aenter__(self):
            return session
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    with patch('app.handlers.admin_handler.get_session', return_value=SessionContext()):
        yield session


@pytest.mark.asyncio
async def test_cmd_edit_store(create_message, state, session_patch):
    """Тест команды редактирования магазина"""
    # Создаем тестовый магазин
    store_svc = StoreService(session_patch)
    store = await store_svc.get_or_create("TestEditStore")
    
    # Вызываем функцию обработчика
    message = create_message()
    await cmd_edit_store(message, state)
    
    # Проверяем, что сообщение было отправлено и состояние установлено
    message.answer.assert_called_once()
    assert "Выберите магазин для редактирования" in message.answer.call_args[0][0]
    
    # Проверяем, что состояние правильно установлено
    assert await state.get_state() == EditStoreStates.waiting_store


@pytest.mark.asyncio
async def test_edit_store_flow(create_message, state, session_patch):
    """Тест полного потока редактирования магазина"""
    # Создаем тестовый магазин
    store_svc = StoreService(session_patch)
    store = await store_svc.get_or_create("FlowTestStore")
    await store_svc.set_plan(store, 100.0)
    
    # Шаг 1: Выбор магазина
    message1 = create_message("FlowTestStore")
    await process_edit_store_selection(message1, state)
    
    # Проверяем состояние после выбора магазина
    assert await state.get_state() == EditStoreStates.waiting_field
    state_data = await state.get_data()
    assert state_data["store_name"] == "FlowTestStore"
    
    # Шаг 2: Выбор поля для редактирования (план)
    message2 = create_message("Изменить план")
    await process_edit_store_field(message2, state)
    
    # Проверяем состояние после выбора поля
    assert await state.get_state() == EditStoreStates.waiting_value
    state_data = await state.get_data()
    assert state_data["edit_field"] == "plan"
    
    # Создаем сессию для проверки изменений в базе
    store_service = StoreService(session_patch)
    
    # Шаг 3: Ввод нового значения
    # Создаем новый AsyncMock для message3, чтобы не конфликтовать с предыдущими вызовами
    message3 = create_message("200.5")
    
    # Патчим store_service.get_by_name в процессе выполнения process_edit_store_value
    with patch('app.services.store_service.StoreService.get_by_name', return_value=store):
        with patch('app.services.store_service.StoreService.set_plan', return_value=store):
            await process_edit_store_value(message3, state)
    
    # Проверяем, что состояние очищено
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_cmd_edit_manager(create_message, state, session_patch):
    """Тест команды редактирования менеджера"""
    # Создаем тестового менеджера
    user_svc = UserService(session_patch)
    manager = await user_svc.get_or_create("TestEdit", "Manager", "manager")
    
    # Патчим UserService.get_all_users, чтобы вернуть список, включающий созданного менеджера
    with patch('app.services.user_service.UserService.get_all_users', return_value=[manager]):
        # Вызываем функцию обработчика
        message = create_message()
        await cmd_edit_manager(message, state)
        
        # Проверяем, что сообщение было отправлено и состояние установлено
        message.answer.assert_called_once()
        assert "Выберите менеджера для редактирования" in message.answer.call_args[0][0]
        
        # Проверяем, что состояние правильно установлено
        assert await state.get_state() == EditManagerStates.waiting_manager


@pytest.mark.asyncio
async def test_edit_manager_flow(create_message, state, session_patch):
    """Тест полного потока редактирования менеджера"""
    # Создаем тестового менеджера и магазин
    user_svc = UserService(session_patch)
    store_svc = StoreService(session_patch)
    
    manager = await user_svc.get_or_create("FlowTest", "Manager", "manager")
    store = await store_svc.get_or_create("ManagerTestStore")
    
    # Шаг 1: Выбор менеджера
    message1 = create_message("FlowTest Manager")
    await process_edit_manager_selection(message1, state)
    
    # Проверяем состояние после выбора менеджера
    assert await state.get_state() == EditManagerStates.waiting_field
    state_data = await state.get_data()
    assert state_data["manager_name"] == "FlowTest Manager"
    
    # Шаг 2: Выбор поля для редактирования (магазин)
    message2 = create_message("Изменить магазин")
    
    # Патчим StoreService.list_stores, чтобы вернуть список с созданным магазином
    with patch('app.services.store_service.StoreService.list_stores', return_value=[store]):
        await process_edit_manager_field(message2, state)
    
    # Проверяем состояние после выбора поля
    assert await state.get_state() == EditManagerStates.waiting_value
    state_data = await state.get_data()
    assert state_data["edit_field"] == "store"
    assert state_data["first_name"] == "FlowTest"
    assert state_data["last_name"] == "Manager"
    
    # Шаг 3: Выбор магазина
    message3 = create_message("ManagerTestStore")
    
    # Патчим необходимые методы для успешного выполнения flow
    with patch('app.services.user_service.UserService.get_by_name', return_value=manager):
        with patch('app.services.store_service.StoreService.get_by_name', return_value=store):
            with patch('app.services.user_service.UserService.assign_store', return_value=manager):
                await process_edit_manager_value(message3, state)
    
    # Проверяем, что состояние очищено
    assert await state.get_state() is None
