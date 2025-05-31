"""
Тест для проверки исправления проблемы с авторизацией администратора
"""

import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.admin_handler import (
    cmd_report,
    cmd_editstore,
    cmd_assign,
    cmd_add_store,
)
from app.services.store_service import StoreService


@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=987654321, from_user_id=987654321):
        message = AsyncMock(spec=Message)
        message.text = text
        message.chat = Chat(id=chat_id, type="private")
        message.from_user = TgUser(id=from_user_id, is_bot=False, first_name="Admin")
        message.answer = AsyncMock()
        message.answer_document = AsyncMock()
        message.answer_photo = AsyncMock()
        return message

    return _create_message


@pytest.fixture
def state():
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key="test")
    return state


@pytest.fixture
def admin_chat_ids():
    from app.core.config import ADMIN_CHAT_IDS

    original_ids = ADMIN_CHAT_IDS[:]
    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend([987654321])
    yield ADMIN_CHAT_IDS

    ADMIN_CHAT_IDS.clear()
    ADMIN_CHAT_IDS.extend(original_ids)


@pytest.mark.asyncio
async def test_admin_report_after_other_commands(create_message, state, admin_chat_ids):
    """
    Тест: администратор должен иметь возможность использовать /report
    после использования других команд, которые очищают состояние FSM
    """

    await state.update_data(
        user_id=1, first_name="admin1", last_name="Admin", role="admin"
    )

    data = await state.get_data()
    assert data.get("user_id") == 1

    message = create_message()

    with patch("app.handlers.admin_handler.get_session"):
        with patch(
            "app.handlers.admin_handler.StoreService.list_stores", return_value=[]
        ):
            await cmd_editstore(message, state)

    data_after_editstore = await state.get_data()
    assert data_after_editstore.get("user_id") is None

    message_report = create_message()

    with patch("app.handlers.admin_handler.get_session"):
        with patch("app.handlers.admin_handler.RevenueService") as mock_revenue_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.export_report.return_value = (
                b"fake_excel",
                "filename",
            )
            mock_service_instance.get_matryoshka_data.return_value = []
            mock_revenue_service.return_value = mock_service_instance

            await cmd_report(message_report, state)

    message_report.answer.assert_called()
    call_args = message_report.answer.call_args[0][0]
    assert "авторизуйтесь" not in call_args.lower()
    assert "нет данных для построения отчета" in call_args


@pytest.mark.asyncio
async def test_admin_report_works_without_fsm_state(
    create_message, state, admin_chat_ids
):
    """
    Тест: администратор должен иметь возможность использовать /report
    даже если у него нет данных в FSM состоянии
    """

    await state.clear()
    data = await state.get_data()
    assert data.get("user_id") is None

    message = create_message()

    with patch("app.handlers.admin_handler.get_session"):
        with patch("app.handlers.admin_handler.RevenueService") as mock_revenue_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.export_report.return_value = (
                b"fake_excel",
                "filename",
            )
            mock_service_instance.get_matryoshka_data.return_value = []
            mock_revenue_service.return_value = mock_service_instance

            await cmd_report(message, state)

    message.answer.assert_called()
    call_args = message.answer.call_args[0][0]
    assert "авторизуйтесь" not in call_args.lower()
    assert "нет данных для построения отчета" in call_args


@pytest.mark.asyncio
async def test_non_admin_cannot_use_report(create_message, state):
    """
    Тест: не-администратор не должен иметь возможность использовать /report
    """

    message = create_message(chat_id=123456789)

    await cmd_report(message, state)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "нет прав администратора" in call_args.lower()
