import asyncio
import io
import pytz
import logging

if __name__ == "__main__":
    import sys
    sys.path.append("./")  # Добавляем корневую директорию в путь для импорта

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

logger = logging.getLogger(__name__)


async def send_daily_report(bot: Bot):
    """Генерирует отчет и отправляет его всем администраторам"""
    try:

        resources_dir = Path(__file__).parent.parent.parent / "resources"
        resources_dir.mkdir(exist_ok=True)
        template_path = str(resources_dir / "bear3.glb")

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

            recipients_info = {}

            for chat_id in ADMIN_CHAT_IDS:
                recipients_info[chat_id] = {
                    "role": "config_admin",
                    "name": f"Config Admin {chat_id }",
                }

            for u in all_users:
                if u.chat_id:
                    if u.role == "admin":
                        recipients_info[u.chat_id] = {
                            "role": "db_admin",
                            "name": f"{u .first_name } {u .last_name }",
                        }
                    elif u.role == "subscriber":
                        recipients_info[u.chat_id] = {
                            "role": "subscriber",
                            "name": f"{u .first_name } {u .last_name }",
                        }

        if not shops_data:
            logger.info("Нет данных для отчета - отправка пропущена")
            return

        matryoshka_buffers = create_matryoshka_collection(
            template_path, shops_data, layout="vertical", max_per_image=2
        )

        config_admins = sum(
            1 for info in recipients_info.values() if info["role"] == "config_admin"
        )
        db_admins = sum(
            1 for info in recipients_info.values() if info["role"] == "db_admin"
        )
        subscribers = sum(
            1 for info in recipients_info.values() if info["role"] == "subscriber"
        )

        logger.info(
            f"Начинаем отправку ежедневного отчета. Получатели: "
            f"админы из конфига: {config_admins }, админы из БД: {db_admins }, подписчики: {subscribers }"
        )

        successful_sends = 0
        failed_sends = 0

        for chat_id in sorted(recipients_info.keys()):
            recipient_info = recipients_info[chat_id]
            role = recipient_info["role"]
            name = recipient_info["name"]

            try:
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

                logger.info(
                    f"✅ Отчет отправлен: {name } (роль: {role }, chat_id: {chat_id })"
                )
                successful_sends += 1

            except Exception as send_error:
                logger.error(
                    f"❌ Ошибка отправки отчета: {name } (роль: {role }, chat_id: {chat_id }): {send_error }"
                )
                failed_sends += 1

        logger.info(
            f"Отправка завершена. Успешно: {successful_sends }, с ошибками: {failed_sends }"
        )

    except Exception as e:
        logger.error(
            f"⚠️ Критическая ошибка при генерации ежедневного отчета: {str (e )}"
        )

        error_message = f"⚠️ Ошибка при генерации ежедневного отчета: {str (e )}"
        for chat_id in ADMIN_CHAT_IDS:
            try:
                await bot.send_message(chat_id, error_message)
                logger.info(
                    f"Уведомление об ошибке отправлено администратору {chat_id }"
                )
            except Exception as notify_error:
                logger.error(
                    f"Не удалось отправить уведомление администратору {chat_id }: {notify_error }"
                )
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
        logger.info(
            f"Планировщик настроен на отправку каждую секунду {second } (тестовый режим)"
        )
    else:
        trigger_args.update({"hour": hour, "minute": minute})
        logger.info(
            f"Планировщик настроен на ежедневную отправку в {hour :02d}:{minute :02d} МСК"
        )

    trigger = CronTrigger(**trigger_args)

    scheduler.add_job(send_daily_report, trigger=trigger, args=[bot])
    try:
        scheduler.start()
        logger.info("Планировщик ежедневных отчетов запущен")
    except RuntimeError as e:
        logger.warning(f"Планировщик уже запущен: {e }")
        pass
    return scheduler


if __name__ == "__main__":
    import app.core.config as config

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    bot = Bot(token=config.BOT_TOKEN)

    logger.info("Запуск тестовой отправки ежедневного отчета")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_daily_report(bot))
    loop.close()
    logger.info("Тестовая отправка завершена")
