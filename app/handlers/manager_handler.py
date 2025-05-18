import logging
import datetime
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from app.core.database import get_session
from app.core.states import RevenueStates
from app.services.user_service import UserService
from app.services.store_service import StoreService
from app.services.revenue_service import RevenueService
from app.utils.menu import get_main_keyboard, MANAGER_MENU_TEXT
from app.utils.validators import validate_revenue_amount
from app.utils.date_utils import format_date_for_display

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("revenue"))
async def cmd_revenue(message: types.Message, state: FSMContext):
    """Команда для ввода выручки"""

    data = await state.get_data()
    user_id = data.get("user_id")

    if not user_id:
        await message.answer("Пожалуйста, сначала авторизуйтесь через команду /start")
        return

    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_by_id(user_id)

        if not user:
            await message.answer(
                "Ошибка: не удалось найти данные пользователя. Пожалуйста, обратитесь к администратору."
            )
            return

        if not user.store_id:
            await message.answer(
                "У вас нет привязки к магазину. Пожалуйста, обратитесь к администратору для настройки."
            )
            return

    today = datetime.date.today()
    dates = [today - datetime.timedelta(days=i) for i in range(8)]

    kb = ReplyKeyboardBuilder()
    for date_obj in dates:
        kb.button(text=date_obj.strftime("%d.%m.%Y"))
    kb.adjust(2)

    await message.answer(
        "Выберите дату для ввода выручки:",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
    await state.set_state(RevenueStates.waiting_date)


@router.message(RevenueStates.waiting_date)
async def process_revenue_date(message: types.Message, state: FSMContext):
    """Обработка выбора даты для ввода выручки"""
    date_str = message.text.strip()

    try:

        date_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()

        today = datetime.date.today()
        if date_obj > today:
            await message.answer(
                "Нельзя вводить выручку за будущую дату. Пожалуйста, выберите другую дату."
            )
            return

        await state.update_data(selected_date=date_obj.isoformat())

        data = await state.get_data()
        user_id = data.get("user_id")

        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_by_id(user_id)

            if not user or not user.store_id:
                await message.answer(
                    "Ошибка: не удалось найти данные пользователя или магазина.",
                    reply_markup=get_main_keyboard("manager"),
                )
                await state.clear()
                return

            store_service = StoreService(session)
            store = await store_service.get_by_id(user.store_id)

            if not store:
                await message.answer(
                    "Ошибка: не удалось найти магазин.",
                    reply_markup=get_main_keyboard("manager"),
                )
                await state.clear()
                return

            revenue_service = RevenueService(session)
            existing_revenue = await revenue_service.get_revenue(
                store.id, date_obj.isoformat()
            )

            message_text = f'Введите выручку за {format_date_for_display (date_obj )} для магазина "{store .name }":'
            if existing_revenue:
                message_text += f"\n\nУже введена выручка: {existing_revenue .amount }. Новое значение заменит старое."

            await message.answer(
                message_text,
                reply_markup=types.ReplyKeyboardRemove(),
            )
            await state.set_state(RevenueStates.waiting_amount)

    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, выберите дату из предложенных вариантов."
        )


@router.message(RevenueStates.waiting_amount)
async def process_revenue_amount(message: types.Message, state: FSMContext):
    """Обработка ввода суммы выручки"""
    amount_str = message.text.strip()

    try:

        amount = validate_revenue_amount(amount_str)

        data = await state.get_data()
        date_str = data.get("selected_date")
        user_id = data.get("user_id")

        if not date_str or not user_id:
            await message.answer(
                "Ошибка: не удалось получить данные о дате или пользователе.",
                reply_markup=get_main_keyboard("manager"),
            )
            await state.clear()
            return

        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_by_id(user_id)

            if not user or not user.store_id:
                await message.answer(
                    "Ошибка: не удалось найти данные пользователя или магазина.",
                    reply_markup=get_main_keyboard("manager"),
                )
                await state.clear()
                return

            store_service = StoreService(session)
            store = await store_service.get_by_id(user.store_id)

            revenue_service = RevenueService(session)
            revenue = await revenue_service.add_revenue(store.id, date_str, amount)

            date_obj = datetime.date.fromisoformat(date_str)
            formatted_date = format_date_for_display(date_obj)

            await message.answer(
                f'✓ Выручка {amount } для магазина "{store .name }" за {formatted_date } успешно сохранена.',
                reply_markup=get_main_keyboard("manager"),
            )
            await state.clear()

    except ValueError as e:
        await message.answer(
            f"Ошибка: {str (e )}. Пожалуйста, введите корректную сумму."
        )


@router.message(Command("status"))
async def cmd_status(message: types.Message, state: FSMContext):
    """Команда для проверки статуса выполнения плана"""

    data = await state.get_data()
    user_id = data.get("user_id")

    if not user_id:
        await message.answer("Пожалуйста, сначала авторизуйтесь через команду /start")
        return

    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_by_id(user_id)

        if not user:
            await message.answer(
                "Ошибка: не удалось найти данные пользователя. Пожалуйста, обратитесь к администратору."
            )
            return

        if not user.store_id:
            await message.answer(
                "У вас нет привязки к магазину. Пожалуйста, обратитесь к администратору для настройки."
            )
            return

        store_service = StoreService(session)
        store = await store_service.get_by_id(user.store_id)

        if not store:
            await message.answer(
                "Ошибка: не удалось найти данные магазина. Пожалуйста, обратитесь к администратору."
            )
            return

        revenue_service = RevenueService(session)
        stats = await revenue_service.get_status(store.id)

        if not stats:
            await message.answer(
                f'📊 Статус выполнения плана для магазина "{store .name }":\n\n'
                f"План на месяц: {store .plan }\n"
                f"Текущая выручка: 0\n"
                f"Процент выполнения: 0%\n\n"
                f"Нет данных о выручке за текущий месяц.",
                reply_markup=get_main_keyboard("manager"),
            )
            return

        message_text = (
            f'📊 Статус выполнения плана для магазина "{store .name }":\n\n'
            f"План на месяц: {stats ['plan']}\n"
            f"Текущая выручка: {stats ['total']}\n"
            f"Процент выполнения: {stats ['percent']}%\n"
        )

        if stats.get("last_date") and stats.get("last_amount"):
            last_date = datetime.date.fromisoformat(stats["last_date"])
            formatted_date = format_date_for_display(last_date)
            message_text += (
                f"\nПоследний ввод: {stats ['last_amount']} ({formatted_date })"
            )

        await message.answer(
            message_text,
            reply_markup=get_main_keyboard("manager"),
        )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда вызова справки для менеджера"""
    await message.answer(
        MANAGER_MENU_TEXT,
        parse_mode="HTML",
        reply_markup=get_main_keyboard("manager"),
    )
