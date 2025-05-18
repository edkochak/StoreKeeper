import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")


admin_ids_str = os.getenv("ADMIN_CHAT_IDS", os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_CHAT_IDS = [
    int(chat_id.strip()) for chat_id in admin_ids_str.split(",") if chat_id.strip()
]

DEFAULT_PLAN = float(os.getenv("DEFAULT_PLAN", "0"))


REDIS_DSN = os.getenv("REDIS_DSN", "redis://localhost:6379/0")
