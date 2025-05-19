import asyncio
from datetime import datetime, timedelta
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from unittest.mock import AsyncMock
from aiogram import Bot

from app.utils.scheduler import schedule_daily_report, send_daily_report


@pytest.mark.asyncio
async def test_schedule_send_daily_report(monkeypatch):
    """
    Проверка, что при планировании задачи на send_daily_report она будет вызвана.
    """
    fake_bot = AsyncMock(spec=Bot)

    called = asyncio.Event()

    async def dummy_send(bot):
        called.set()

    monkeypatch.setattr("app.utils.scheduler.send_daily_report", dummy_send)

    now = datetime.now()
    next_sec = (now + timedelta(seconds=1)).second
    scheduler: AsyncIOScheduler = schedule_daily_report(fake_bot, second=next_sec)

    await asyncio.wait_for(called.wait(), timeout=2)

    assert called.is_set()

    scheduler.shutdown()
