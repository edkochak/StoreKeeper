"""
Тесты для корректировки выручки администратором
"""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.admin_handler import (
    cmd_edit_revenue,
    process_edit_revenue_store,
    process_edit_revenue_date,
    process_edit_revenue_date_message,
    process_edit_revenue_amount,
)
from app.core.states import EditRevenueStates
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.services.revenue_service import RevenueService
from app.models.revenue import Revenue


@pytest.fixture
def create_message():
    def _create_message(text: str):
        message = AsyncMock(spec=Message)
        message.text = text
        message.chat = AsyncMock(spec=Chat)
        message.chat.id = 12345
        message.from_user = AsyncMock(spec=TgUser)
        message.from_user.id = 12345
        message.answer = AsyncMock()
        return message

    return _create_message


@pytest.fixture
def state():
    storage = MemoryStorage()
    return FSMContext(storage=storage, key="chat_12345:user_12345")


@pytest.fixture
def session_patch(session):
    with patch("app.handlers.admin_handler.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = session
        yield session


@pytest.fixture
def admin_chat_ids():

    from app.core.config import ADMIN_CHAT_IDS

    original_ids = ADMIN_CHAT_IDS[:]
    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend([12345])
    yield ADMIN_CHAT_IDS

    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend(original_ids)


@pytest.mark.asyncio
async def test_cmd_edit_revenue_no_stores(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест команды /editrevenue когда нет магазинов"""
    message = create_message("/editrevenue")

    await cmd_edit_revenue(message, state)

    message.answer.assert_called_with("В системе нет магазинов.")


@pytest.mark.asyncio
async def test_cmd_edit_revenue_with_stores(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест команды /editrevenue с магазинами"""

    store_service = StoreService(session_patch)
    store = await store_service.get_or_create("TestEditStore")

    message = create_message("/editrevenue")

    await cmd_edit_revenue(message, state)

    assert await state.get_state() == EditRevenueStates.waiting_store

    message.answer.assert_called()
    call_args = message.answer.call_args[0][0]
    assert "Выберите магазин для корректировки выручки:" in call_args


@pytest.mark.asyncio
async def test_process_edit_revenue_store_selection(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест выбора магазина для корректировки"""

    store_service = StoreService(session_patch)
    store = await store_service.get_or_create("TestEditStore")

    await state.set_state(EditRevenueStates.waiting_store)

    message = create_message("TestEditStore")

    await process_edit_revenue_store(message, state)

    assert await state.get_state() == EditRevenueStates.waiting_date

    data = await state.get_data()
    assert data["store_name"] == "TestEditStore"


@pytest.mark.asyncio
async def test_process_edit_revenue_date_selection(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест выбора даты для корректировки"""

    await state.set_state(EditRevenueStates.waiting_date)
    await state.set_data({"store_name": "TestEditStore", "store_id": 1})

    today = date.today()
    message = create_message(today.strftime("%d.%m.%Y"))

    await process_edit_revenue_date_message(message, state)

    assert await state.get_state() == EditRevenueStates.waiting_amount

    data = await state.get_data()
    assert data["selected_date"] == today.isoformat()


@pytest.mark.asyncio
async def test_process_edit_revenue_amount_new_record(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест ввода суммы для новой записи"""

    store_service = StoreService(session_patch)
    user_service = UserService(session_patch)
    revenue_service = RevenueService(session_patch)

    store = await store_service.get_or_create("TestEditStore")

    await state.set_state(EditRevenueStates.waiting_amount)
    today = date.today()
    await state.set_data(
        {
            "store_id": store.id,
            "store_name": "TestEditStore",
            "revenue_date": today.isoformat(),
            "selected_date": today.isoformat(),
        }
    )

    message = create_message("25000.50")

    await process_edit_revenue_amount(message, state)

    revenue = await revenue_service.get_revenue(store.id, today)
    assert revenue is not None
    assert revenue.amount == 25000.50

    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_process_edit_revenue_amount_update_existing(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест обновления существующей записи"""

    store_service = StoreService(session_patch)
    user_service = UserService(session_patch)
    revenue_service = RevenueService(session_patch)

    store = await store_service.get_or_create("TestEditStore")
    manager = await user_service.get_or_create(
        "System", "Admin", "admin", store_id=store.id
    )

    today = date.today()
    existing_revenue = await revenue_service.create_revenue(
        amount=15000.0, store_id=store.id, manager_id=manager.id, date_obj=today
    )

    await state.set_state(EditRevenueStates.waiting_amount)
    await state.set_data(
        {
            "store_id": store.id,
            "store_name": "TestEditStore",
            "revenue_date": today.isoformat(),
            "selected_date": today.isoformat(),
            "revenue_id": existing_revenue.id,
        }
    )

    message = create_message("30000.75")

    await process_edit_revenue_amount(message, state)

    updated_revenue = await revenue_service.get_revenue(store.id, today)
    assert updated_revenue is not None
    assert updated_revenue.amount == 30000.75
    assert updated_revenue.id == existing_revenue.id


@pytest.mark.asyncio
async def test_edit_revenue_invalid_amount(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест ввода некорректной суммы"""
    await state.set_state(EditRevenueStates.waiting_amount)
    await state.set_data(
        {
            "store_id": 1,
            "store_name": "TestEditStore",
            "revenue_date": date.today().isoformat(),
            "selected_date": date.today().isoformat(),
        }
    )

    message = create_message("не число")

    await process_edit_revenue_amount(message, state)

    message.answer.assert_called()
    call_args = message.answer.call_args[0][0]
    assert "Пожалуйста, введите число" in call_args

    assert await state.get_state() == EditRevenueStates.waiting_amount


@pytest.mark.asyncio
async def test_edit_revenue_invalid_store(
    create_message, state, session_patch, admin_chat_ids
):
    """Тест выбора несуществующего магазина"""
    await state.set_state(EditRevenueStates.waiting_store)

    message = create_message("НесуществующийМагазин")

    await process_edit_revenue_store(message, state)

    message.answer.assert_called()
    call_args = message.answer.call_args[0][0]
    assert "Магазин не найден" in call_args

    assert await state.get_state() == EditRevenueStates.waiting_store
