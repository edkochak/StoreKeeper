import asyncio
import io
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from aiogram.types import InputFile
from app.core.config import ADMIN_CHAT_IDS
from app.core.database import get_session
from app.services.revenue_service import RevenueService


async def send_daily_report(bot: Bot):
    """Генерирует отчет и отправляет его всем администраторам"""
    async with get_session() as session:
        rev_svc = RevenueService(session)
        excel_bytes, images = await rev_svc.export_report()

    for chat_id in ADMIN_CHAT_IDS:
        await bot.send_document(
            chat_id, io.BytesIO(excel_bytes), filename="report.xlsx"
        )
        for name, img_bytes in images.items():
            await bot.send_photo(chat_id, io.BytesIO(img_bytes), filename=name)


def schedule_daily_report(
    bot: Bot, hour: int = 22, minute: int = 30, second: int = None
) -> AsyncIOScheduler:
    """Планирует ежедневную отправку отчета в 22:30 по часовому поясу МСК"""
    scheduler = AsyncIOScheduler()

    tz = pytz.timezone("Europe/Moscow")
    trigger_args = {"timezone": tz}
    if second is not None:
        trigger_args["second"] = second
    else:
        trigger_args.update({"hour": hour, "minute": minute})
    trigger = CronTrigger(**trigger_args)

    scheduler.add_job(send_daily_report, trigger=trigger, args=[bot])
    try:
        scheduler.start()
    except RuntimeError:
        pass
    return scheduler
