import pytest
from unittest.mock import AsyncMock
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.manager_handler import (
    cmd_revenue,
    process_revenue_amount,
    cmd_status,
)


@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=333, from_user_id=333):
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
async def test_cmd_revenue_without_auth(create_message, state):
    msg = create_message()
    await cmd_revenue(msg, state)
    msg.answer.assert_awaited()


@pytest.mark.asyncio
async def test_process_revenue_amount_invalid_input(create_message, state):
    await state.update_data(user_id=None, selected_date=None)
    msg = create_message(text="not_a_number")
    await process_revenue_amount(msg, state)
    msg.answer.assert_awaited()


@pytest.mark.asyncio
async def test_process_revenue_amount_missing_state_ok(create_message, state):
    # Валидное число, но нет selected_date и user_id в состоянии — должен прийти ответ об ошибке
    msg = create_message(text="123.45")
    await process_revenue_amount(msg, state)
    msg.answer.assert_awaited()


@pytest.mark.asyncio
async def test_cmd_status_without_auth(create_message, state):
    msg = create_message()
    await cmd_status(msg, state)
    msg.answer.assert_awaited()
