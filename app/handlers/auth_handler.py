from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.core.states import AuthStates
from app.core.config import ADMIN_CHAT_IDS, SECRET_ADMIN_AUTH
from app.core.database import get_session
from app.services.user_service import UserService
from app.utils.menu import get_menu_text, get_main_keyboard
import logging

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
    # Специальная авторизация администратора по коду
    if text.lower() == SECRET_ADMIN_AUTH.lower():
        await state.update_data(
            user_id=None,
            first_name="Администратор",
            last_name="1999",
            role="admin"
        )
        # Добавляем chat_id в список для рассылки
        if message.chat.id not in ADMIN_CHAT_IDS:
            ADMIN_CHAT_IDS.append(message.chat.id)
        await message.answer(
            f"✅ Вы авторизованы как администратор {SECRET_ADMIN_AUTH}.",
            reply_markup=get_main_keyboard("admin"),
        )
        await message.answer(get_menu_text("admin"), parse_mode="HTML")
        await state.set_state(None)
        return
    parts = text.split()
    if len(parts) < 2:
        await message.answer("Пожалуйста, введите имя и фамилию через пробел:")
        return

    first_name, last_name = parts[0], " ".join(parts[1:])
    role = "admin" if message.chat.id in ADMIN_CHAT_IDS else "manager"

    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_by_name(first_name, last_name)

        if not user:
            await message.answer(
                f"❌ Авторизация не удалась: пользователь {first_name } {last_name } не найден в системе."
            )
            await state.clear()
            return

        if user.role != role:
            await message.answer(
                f"❌ Авторизация не удалась: несоответствие роли пользователя."
            )
            await state.clear()
            return

    logger.info("Пользователь авторизован: %s %s (%s)", first_name, last_name, role)
    await state.update_data(
        user_id=user.id, first_name=first_name, last_name=last_name, role=role
    )

    store_info = f", ваш магазин: {user .store .name }" if user.store_id else ""
    await message.answer(
        f"✅ Вы успешно авторизованы как {role } {first_name } {last_name }{store_info }.",
        reply_markup=get_main_keyboard(role),
    )
    await message.answer(get_menu_text(role), parse_mode="HTML")

    await state.set_state(None)
