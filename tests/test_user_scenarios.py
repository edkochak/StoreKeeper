import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, CallbackQuery, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.manager_handler import cmd_revenue, cmd_status
from app.models.store import Store
from app.models.user import User
from app.models.revenue import Revenue
from app.services.user_service import UserService
from app.services.store_service import StoreService
from app.services.revenue_service import RevenueService
from app.core.states import RevenueStates


@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=123456789, from_user_id=123456789):
        message = AsyncMock(spec=Message)
        message.text = text
        message.chat = Chat(id=chat_id, type="private")
        message.from_user = TgUser(id=from_user_id, is_bot=False, first_name="Test")
        message.answer = AsyncMock()
        message.answer.return_value = AsyncMock()
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

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch(
        "app.handlers.manager_handler.get_session", return_value=SessionContext()
    ):
        yield session


@pytest.mark.asyncio
async def test_manager_revenue_input_flow(create_message, state, session_patch):
    """Тест сценария ввода выручки менеджером"""

    user_service = UserService(session_patch)
    store_service = StoreService(session_patch)

    store = await store_service.get_or_create("TestFlow магазин")
    store.id = 1
    manager = await user_service.get_or_create(
        "TestFlow", "Менеджер", "manager", store.id
    )

    await state.update_data(user_id=manager.id)

    with patch("app.services.user_service.UserService.get_by_id", return_value=manager):
        with patch(
            "app.services.store_service.StoreService.get_by_id", return_value=store
        ):

            message = create_message("/revenue")
            await cmd_revenue(message, state)

            message.answer.assert_called_once()
            assert "выберите дату" in message.answer.call_args[0][0].lower()

            await state.update_data(selected_date="2023-05-15")

            await state.set_state(RevenueStates.waiting_amount)

            message.answer.reset_mock()

            message2 = create_message("10000")

            assert await state.get_state() == RevenueStates.waiting_amount

            await state.clear()


@pytest.mark.asyncio
async def test_manager_status_check(create_message, state, session_patch):
    """Тест сценария проверки статуса выполнения плана менеджером"""

    user_service = UserService(session_patch)
    store_service = StoreService(session_patch)
    revenue_service = RevenueService(session_patch)

    store = await store_service.get_or_create("TestStatus магазин")
    store.id = 2
    await store_service.set_plan(store, 50000.0)
    manager = await user_service.get_or_create(
        "TestStatus", "Менеджер", "manager", store.id
    )

    await state.update_data(user_id=manager.id)

    stats = {
        "total": 15000.0,
        "plan": 50000.0,
        "percent": 30,
        "last_date": "2023-05-20",
        "last_amount": 2000.0,
    }

    with patch("app.services.user_service.UserService.get_by_id", return_value=manager):
        with patch(
            "app.services.revenue_service.RevenueService.get_status", return_value=stats
        ):

            message = create_message("/status")
            await cmd_status(message, state)

            message.answer.assert_called_once()
            call_args = message.answer.call_args[0][0]
            assert "30%" in call_args
            assert "50000" in call_args
            assert "15000" in call_args
