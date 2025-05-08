import asyncio
import logging
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import types

# Добавляем корень проекта в PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import BOT_TOKEN, REDIS_DSN
from app.core.database import engine, Base
from app.handlers.auth_handler import router as auth_router
from app.handlers.revenue_handler import router as revenue_router
from app.handlers.admin_handler import router as admin_router
from app.handlers.plan_handler import router as plan_router


async def on_startup():
    # Создаем таблицы в БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    # Используем Redis для хранения состояний между перезапусками
    storage = RedisStorage.from_url(REDIS_DSN)

    bot = Bot(token=BOT_TOKEN)
    # Удаляем все вебхуки перед началом polling
    await bot.delete_webhook(drop_pending_updates=True)

    # Используем RedisStorage вместо MemoryStorage
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(auth_router)
    dp.include_router(revenue_router)
    dp.include_router(admin_router)
    dp.include_router(plan_router)

    # Глобальный обработчик ошибок aiogram v3
    async def global_error_handler(exception: Exception, update: object = None) -> bool:
        # Логируем ошибку
        logging.getLogger("aiogram").error("Exception %s, update %s", exception, update)
        return True

    dp.errors.register(global_error_handler)

    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main())
