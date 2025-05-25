from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.core.states import AuthStates
from app.core.config import ADMIN_CHAT_IDS, SECRET_SUBSCRIBER_AUTH
from app.core.database import get_session
from app.services.user_service import UserService
from app.utils.menu import get_menu_text, get_main_keyboard
import logging
import uuid

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):

    if message.chat.id in ADMIN_CHAT_IDS:

        admin_index = ADMIN_CHAT_IDS.index(message.chat.id) + 1
        first_name = f"admin{admin_index }"
        last_name = "Admin"

        async with get_session() as session:
            user_service = UserService(session)

            user = await user_service.get_by_name(first_name, last_name)
            if not user:
                user = await user_service.get_or_create(first_name, last_name, "admin")
                logger.info(f"Автоматически создан администратор: {first_name }")

            user = await user_service.update_chat_id(user, message.chat.id)

        await state.update_data(
            user_id=user.id, first_name=first_name, last_name=last_name, role="admin"
        )

        await message.answer(
            f"✅ Вы авторизованы как администратор {first_name }.",
            reply_markup=get_main_keyboard("admin"),
        )
        await message.answer(get_menu_text("admin"), parse_mode="HTML")
        return

    await message.answer(
        "Здравствуйте! Пожалуйста, введите ваше имя и фамилию через пробел для авторизации:"
    )
    await state.set_state(AuthStates.waiting_name)


@router.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext):

    data = await state.get_data()
    role = data.get("role")

    await message.answer(
        get_menu_text(role), parse_mode="HTML", reply_markup=get_main_keyboard(role)
    )


@router.message(AuthStates.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if text == SECRET_SUBSCRIBER_AUTH:
        async with get_session() as session:
            user_service = UserService(session)

            first_name = "Subscriber"
            last_name = str(message.chat.id)

            user = await user_service.get_or_create(first_name, last_name, "subscriber")

            await user_service.update_chat_id(user, message.chat.id)

            logger.info(
                "Подписчик авторизован: %s %s (chat_id: %s)",
                first_name,
                last_name,
                message.chat.id,
            )

            await state.update_data(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                role="subscriber",
            )

            await message.answer(
                "✅ Вы успешно подписались на ежедневную рассылку отчетов."
            )
            await state.set_state(None)
            return

    parts = text.split()
    if len(parts) < 2:
        await message.answer("Пожалуйста, введите имя и фамилию через пробел:")
        return

    first_name, last_name = parts[0], " ".join(parts[1:])

    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_by_name(first_name, last_name)

        if not user:
            await message.answer(
                f"❌ Авторизация не удалась: пользователь {first_name } {last_name } не найден в системе."
            )
            await state.clear()
            return

        role = user.role

        await user_service.update_chat_id(user, message.chat.id)

        if role not in ("admin", "manager", "subscriber"):
            await message.answer(
                f"❌ Авторизация не удалась: неизвестная роль {role }."
            )
            await state.clear()
            return

    logger.info("Пользователь авторизован: %s %s (%s)", first_name, last_name, role)
    await state.update_data(
        user_id=user.id, first_name=first_name, last_name=last_name, role=role
    )

    if role == "subscriber":
        await message.answer(
            "✅ Вы успешно подписались на ежедневную рассылку отчетов.",
        )
        await state.set_state(None)
        return

    store_info = f", ваш магазин: {user .store .name }" if user.store_id else ""
    await message.answer(
        f"✅ Вы успешно авторизованы как {role } {first_name } {last_name }{store_info }.",
        reply_markup=get_main_keyboard(role),
    )
    await message.answer(get_menu_text(role), parse_mode="HTML")

    await state.set_state(None)
