import asyncio
import datetime
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_task_executes_next_second():
    """
    Проверка, что задача, запланированная на следующую секунду, выполнится.
    """

    loop = asyncio.get_running_loop()
    scheduler = AsyncIOScheduler(event_loop=loop)

    mock_job = AsyncMock()

    now = datetime.datetime.now()
    next_sec = (now + datetime.timedelta(seconds=1)).second

    trigger = CronTrigger(second=str(next_sec))

    scheduler.add_job(mock_job, trigger=trigger)
    scheduler.start()

    await asyncio.sleep(1.2)

    assert mock_job.call_count >= 1

    scheduler.shutdown()
