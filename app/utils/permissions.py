from app.core.config import ADMIN_CHAT_IDS
from app.core.database import get_session
from app.services.user_service import UserService


async def is_admin_chat(chat_id: int) -> bool:
    """
    Проверяет, является ли чат административным:
    - либо chat_id присутствует в ADMIN_CHAT_IDS (.env)
    - либо в БД есть пользователь с таким chat_id и ролью "admin"
    Ошибки БД перехватываются и трактуются как отсутствие прав.
    """
    if chat_id in ADMIN_CHAT_IDS:
        return True

    try:
        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.repo.get_by_chat_id(chat_id)
            return bool(user and user.role == "admin")
    except Exception:
        return False
