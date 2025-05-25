"""
Middleware для автоматического обновления chat_id пользователя
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, Update
from aiogram.fsm.context import FSMContext
from app.core.database import get_session
from app.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)


class UpdateChatIdMiddleware(BaseMiddleware):
    """
    Middleware для автоматического обновления chat_id пользователя при каждом взаимодействии
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:

        state: FSMContext = data.get("state")
        if not state:
            return await handler(event, data)

        user_data = await state.get_data()
        user_id = user_data.get("user_id")

        if user_id:
            try:
                async with get_session() as session:
                    user_service = UserService(session)
                    user = await user_service.get_by_id(user_id)

                    if user and user.chat_id != event.chat.id:
                        await user_service.update_chat_id(user, event.chat.id)
                        logger.info(
                            f"Chat ID обновлен для пользователя {user .first_name } {user .last_name }"
                        )

            except Exception as e:
                logger.error(f"Ошибка при обновлении chat_id: {e }")

        return await handler(event, data)
