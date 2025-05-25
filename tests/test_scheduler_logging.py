import pytest
import io
import logging
from unittest.mock import AsyncMock, patch
from aiogram import Bot
from types import SimpleNamespace
from app.utils.scheduler import send_daily_report


@pytest.mark.asyncio
async def test_send_daily_report_detailed_logging(caplog):
    """Тест детального логирования при отправке отчетов"""

    caplog.set_level(logging.INFO, logger="app.utils.scheduler")

    fake_bot = AsyncMock(spec=Bot)
    fake_bot.send_document = AsyncMock()
    fake_bot.send_photo = AsyncMock()
    fake_bot.send_message = AsyncMock()

    excel_data = b"excelbytes"
    images_data = {"chart1.png": b"img1", "chart2.png": b"img2"}
    shops_data = [
        {"title": "Магазин А", "fill_percent": 90},
        {"title": "Магазин Б", "fill_percent": 70},
    ]

    matryoshka_buffer = io.BytesIO(b"matryoshka_data")

    class DummyRevService:
        async def export_report(self):
            return excel_data, images_data

        async def get_matryoshka_data(self):
            return shops_data

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = None
    mock_session_cm.__aexit__.return_value = None

    dummy_users = [
        SimpleNamespace(
            id=300, role="admin", chat_id=300300, first_name="Админ", last_name="Иванов"
        ),
        SimpleNamespace(
            id=400,
            role="subscriber",
            chat_id=400400,
            first_name="Подписчик",
            last_name="Петров",
        ),
        SimpleNamespace(
            id=500,
            role="manager",
            chat_id=500500,
            first_name="Менеджер",
            last_name="Сидоров",
        ),
        SimpleNamespace(
            id=600,
            role="subscriber",
            chat_id=None,
            first_name="Без",
            last_name="ChatId",
        ),
    ]

    class DummyUserService:
        def __init__(self, session):
            pass

        async def get_all_users(self):
            return dummy_users

    config_admin_ids = [100100, 200200]

    with (
        patch("app.utils.scheduler.get_session", return_value=mock_session_cm),
        patch("app.utils.scheduler.RevenueService", return_value=DummyRevService()),
        patch("app.utils.scheduler.UserService", return_value=DummyUserService(None)),
        patch("app.utils.scheduler.ADMIN_CHAT_IDS", config_admin_ids),
        patch(
            "app.utils.scheduler.create_matryoshka_collection",
            return_value=[matryoshka_buffer],
        ),
        patch("app.utils.scheduler.os.path.exists", return_value=True),
    ):
        await send_daily_report(fake_bot)

    log_messages = [record.message for record in caplog.records]

    stats_log = None
    for msg in log_messages:
        if "Начинаем отправку ежедневного отчета" in msg:
            stats_log = msg
            break

    assert stats_log is not None
    assert "админы из конфига: 2" in stats_log
    assert "админы из БД: 1" in stats_log
    assert "подписчики: 1" in stats_log

    successful_sends = [msg for msg in log_messages if "✅ Отчет отправлен:" in msg]
    assert len(successful_sends) == 4

    config_admin_logs = [
        msg
        for msg in successful_sends
        if "Config Admin" in msg and "роль: config_admin" in msg
    ]
    assert len(config_admin_logs) == 2

    db_admin_logs = [
        msg
        for msg in successful_sends
        if "Админ Иванов" in msg and "роль: db_admin" in msg
    ]
    assert len(db_admin_logs) == 1

    subscriber_logs = [
        msg
        for msg in successful_sends
        if "Подписчик Петров" in msg and "роль: subscriber" in msg
    ]
    assert len(subscriber_logs) == 1

    final_stats = None
    for msg in log_messages:
        if "Отправка завершена. Успешно:" in msg:
            final_stats = msg
            break

    assert final_stats is not None
    assert "Успешно: 4" in final_stats
    assert "с ошибками: 0" in final_stats

    manager_logs = [msg for msg in log_messages if "Менеджер Сидоров" in msg]
    assert len(manager_logs) == 0

    no_chatid_logs = [msg for msg in log_messages if "Без ChatId" in msg]
    assert len(no_chatid_logs) == 0


@pytest.mark.asyncio
async def test_send_daily_report_error_logging(caplog):
    """Тест логирования ошибок при отправке отчетов"""

    caplog.set_level(logging.INFO, logger="app.utils.scheduler")

    fake_bot = AsyncMock(spec=Bot)

    async def failing_send_document(chat_id, *args, **kwargs):
        if chat_id == 100100:
            raise Exception("Telegram API Error")
        return AsyncMock()

    fake_bot.send_document = AsyncMock(side_effect=failing_send_document)
    fake_bot.send_photo = AsyncMock()
    fake_bot.send_message = AsyncMock()

    excel_data = b"excelbytes"
    images_data = {"chart1.png": b"img1"}
    shops_data = [{"title": "Магазин", "fill_percent": 85}]
    matryoshka_buffer = io.BytesIO(b"matryoshka_data")

    class DummyRevService:
        async def export_report(self):
            return excel_data, images_data

        async def get_matryoshka_data(self):
            return shops_data

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = None
    mock_session_cm.__aexit__.return_value = None

    dummy_users = [
        SimpleNamespace(
            id=300, role="admin", chat_id=300300, first_name="Тест", last_name="Админ"
        ),
    ]

    class DummyUserService:
        def __init__(self, session):
            pass

        async def get_all_users(self):
            return dummy_users

    with (
        patch("app.utils.scheduler.get_session", return_value=mock_session_cm),
        patch("app.utils.scheduler.RevenueService", return_value=DummyRevService()),
        patch("app.utils.scheduler.UserService", return_value=DummyUserService(None)),
        patch("app.utils.scheduler.ADMIN_CHAT_IDS", [100100, 200200]),
        patch(
            "app.utils.scheduler.create_matryoshka_collection",
            return_value=[matryoshka_buffer],
        ),
        patch("app.utils.scheduler.os.path.exists", return_value=True),
    ):
        await send_daily_report(fake_bot)

    log_messages = [record.message for record in caplog.records]

    error_logs = [msg for msg in log_messages if "❌ Ошибка отправки отчета:" in msg]
    assert len(error_logs) == 1
    assert "Config Admin 100100" in error_logs[0]
    assert "Telegram API Error" in error_logs[0]

    success_logs = [msg for msg in log_messages if "✅ Отчет отправлен:" in msg]
    assert len(success_logs) == 2

    final_stats = None
    for msg in log_messages:
        if "Отправка завершена. Успешно:" in msg:
            final_stats = msg
            break

    assert final_stats is not None
    assert "Успешно: 2" in final_stats
    assert "с ошибками: 1" in final_stats
