import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import app.handlers.auth_handler as auth_mod
from app.core.config import SECRET_SUBSCRIBER_AUTH


class DummyMessage:
    def __init__(self, text, chat_id):
        self.text = text
        self.chat = SimpleNamespace(id=chat_id)
        self.answer = AsyncMock()


class DummyState:
    def __init__(self):
        self.update_data = AsyncMock()
        self.set_state = AsyncMock()
        self.clear = AsyncMock()


@pytest.mark.asyncio
async def test_subscriber_authorization(monkeypatch):

    chat_id = 500
    msg = DummyMessage(SECRET_SUBSCRIBER_AUTH, chat_id)
    state = DummyState()

    dummy_user = SimpleNamespace(
        id=123, first_name="Subscriber", last_name=str(chat_id), role="subscriber"
    )

    class DummyCM:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(auth_mod, "get_session", lambda: DummyCM())
    monkeypatch.setattr(
        auth_mod,
        "UserService",
        lambda session: SimpleNamespace(
            get_or_create=AsyncMock(return_value=dummy_user),
            update_chat_id=AsyncMock(return_value=dummy_user),
        ),
    )

    await auth_mod.process_name(msg, state)

    state.update_data.assert_called_once_with(
        user_id=123,
        first_name="Subscriber",
        last_name=str(chat_id),
        role="subscriber",
    )

    msg.answer.assert_called_once_with(
        "✅ Вы успешно подписались на ежедневную рассылку отчетов."
    )

    state.set_state.assert_called_once_with(None)
