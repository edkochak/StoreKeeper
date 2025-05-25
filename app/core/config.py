import os
from dotenv import load_dotenv
from typing import List

load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")


admin_ids_str = os.getenv("ADMIN_CHAT_IDS", os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_CHAT_IDS = [
    int(chat_id.strip()) for chat_id in admin_ids_str.split(",") if chat_id.strip()
]


REDIS_DSN = os.getenv("REDIS_DSN", "redis://localhost:6379/0")


SECRET_ADMIN_AUTH = os.getenv("SECRET_ADMIN_AUTH", "Администратор 1999")
SECRET_SUBSCRIBER_AUTH = os.getenv("SECRET_SUBSCRIBER_AUTH", "Подписаться")
