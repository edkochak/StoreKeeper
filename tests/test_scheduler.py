import pytest
import asyncio
import io
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from unittest.mock import AsyncMock, patch
from aiogram import Bot

from app.utils.scheduler import schedule_daily_report, send_daily_report
from app.core.config import ADMIN_CHAT_IDS


def test_schedule_daily_report_trigger_timezone():
    """Проверка, что задача запланирована на 22:30 по МСК"""
    fake_bot = AsyncMock(spec=Bot)
    scheduler: AsyncIOScheduler = schedule_daily_report(fake_bot)
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    trigger = job.trigger

    assert isinstance(trigger, CronTrigger)

    trigger_str = str(trigger)

    assert "hour='22'" in trigger_str
    assert "minute='30'" in trigger_str

    tz = trigger.timezone

    assert getattr(tz, "zone", str(tz)) == "Europe/Moscow"


@pytest.mark.asyncio
async def test_send_daily_report():
    """Тест отправки отчета админам"""

    fake_bot = AsyncMock(spec=Bot)
    fake_bot.send_document = AsyncMock()
    fake_bot.send_photo = AsyncMock()
    fake_bot.send_message = AsyncMock()

    excel_data = b"excelbytes"
    images_data = {"chart1.png": b"img1", "chart2.png": b"img2"}
    shops_data = [
        {"title": "Магазин 1", "fill_percent": 80},
        {"title": "Магазин 2", "fill_percent": 60},
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

    with patch("app.utils.scheduler.get_session", return_value=mock_session_cm), patch(
        "app.utils.scheduler.RevenueService", return_value=DummyRevService()
    ), patch("app.utils.scheduler.ADMIN_CHAT_IDS", [100, 200]), patch(
        "app.utils.scheduler.create_matryoshka_collection",
        return_value=[matryoshka_buffer],
    ), patch(
        "app.utils.scheduler.os.path.exists", return_value=True
    ):

        await send_daily_report(fake_bot)

    assert fake_bot.send_document.call_count == 2

    assert fake_bot.send_photo.call_count == 2

    first_doc_call_args = fake_bot.send_document.call_args_list[0][0]
    assert first_doc_call_args[0] == 100

    first_photo_call_args = fake_bot.send_photo.call_args_list[0][0]
    assert first_photo_call_args[0] == 100

    first_photo_call_kwargs = fake_bot.send_photo.call_args_list[0][1]
    assert "Выполнение плана: Магазин 1, Магазин 2" in first_photo_call_kwargs.get(
        "caption", ""
    )
