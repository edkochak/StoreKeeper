import asyncio
import io
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from aiogram.types import BufferedInputFile
from app.core.config import ADMIN_CHAT_IDS
from app.core.database import get_session
from app.services.revenue_service import RevenueService
from app.services.user_service import UserService
from app.utils.matryoshka import create_matryoshka_collection
from pathlib import Path
import os


async def send_daily_report(bot: Bot):
    """Генерирует отчет и отправляет его всем администраторам"""
    try:

        resources_dir = Path(__file__).parent.parent.parent / "resources"
        resources_dir.mkdir(exist_ok=True)
        template_path = str(resources_dir / "matryoshka_template.png")

        if not os.path.exists(template_path):
            from PIL import Image, ImageDraw

            img = Image.new("RGBA", (300, 500), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            draw.ellipse((50, 100, 250, 450), outline=(0, 0, 0), width=3)
            img.save(template_path)

        async with get_session() as session:
            rev_svc = RevenueService(session)
            excel_bytes, images = await rev_svc.export_report()

            shops_data = await rev_svc.get_matryoshka_data()
            shops_data.sort(key=lambda x: x["fill_percent"], reverse=True)

            user_svc = UserService(session)
            all_users = await user_svc.get_all_users()
            db_admin_ids = []
            subscriber_ids = []
            for u in all_users:
                if u.role == "admin":
                    cid = u.chat_id
                    if cid:
                        db_admin_ids.append(cid)
                if u.role == "subscriber":
                    cid = u.chat_id
                    if cid:
                        subscriber_ids.append(cid)

        if not shops_data:
            return

        matryoshka_buffers = create_matryoshka_collection(
            template_path, shops_data, layout="vertical", max_per_image=2
        )

        recipients = set(ADMIN_CHAT_IDS) | set(db_admin_ids) | set(subscriber_ids)
        for chat_id in sorted(recipients):
            await bot.send_document(
                chat_id,
                BufferedInputFile(excel_bytes, filename="revenue_report.xlsx"),
                caption="Подробный отчет по выручке магазинов",
            )

            for i, matryoshka_buf in enumerate(matryoshka_buffers, 1):
                stores_in_image = shops_data[(i - 1) * 2 : i * 2]
                stores_names = ", ".join([s["title"] for s in stores_in_image])

                await bot.send_photo(
                    chat_id,
                    BufferedInputFile(
                        matryoshka_buf.getvalue(),
                        filename=f"report_matryoshka_{i }.png",
                    ),
                    caption=f"📊 Выполнение плана: {stores_names }",
                )

    except Exception as e:

        error_message = f"⚠️ Ошибка при генерации ежедневного отчета: {str (e )}"
        for chat_id in ADMIN_CHAT_IDS:
            try:
                await bot.send_message(chat_id, error_message)
            except Exception:
                print(
                    f"Не удалось отправить сообщение администратору {chat_id }: {error_message }"
                )


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


if __name__ == "__main__":
    import app.core.config as config

    bot = Bot(token=config.BOT_TOKEN)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_daily_report(bot))
    loop.close()
