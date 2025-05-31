from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.core.config import ADMIN_CHAT_IDS
from app.core.states import PlanStates
from app.core.database import get_session
from app.services.store_service import StoreService
from app.services.revenue_service import RevenueService
from app.utils.menu import get_main_keyboard
import logging
import datetime

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("setplan"))
async def cmd_setplan(message: types.Message, state: FSMContext):
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer("У вас нет прав для установки плана.")
        return

    async with get_session() as session:
        stores = await StoreService(session).list_stores()

    kb = ReplyKeyboardBuilder()
    for store in stores:
        kb.button(text=store.name)
    kb.adjust(2)

    await message.answer(
        "Выберите магазин для установки плана:",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
    await state.set_state(PlanStates.waiting_store)


@router.message(PlanStates.waiting_store)
async def process_plan_store(message: types.Message, state: FSMContext):
    await state.update_data(store_name=message.text)

    kb = InlineKeyboardBuilder()
    current_date = datetime.datetime.now()

    for i in range(12):
        month = current_date.month + i
        year = current_date.year

        if month > 12:
            month -= 12
            year += 1

        month_names = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь",
        ]

        button_text = f"{month_names [month -1 ]} {year }"
        callback_data = f"month_{month }_{year }"

        kb.button(text=button_text, callback_data=callback_data)

    kb.adjust(2)

    await message.answer(
        "Выберите месяц для установки плана:", reply_markup=kb.as_markup()
    )
    await state.set_state(PlanStates.waiting_month)


@router.callback_query(PlanStates.waiting_month)
async def process_plan_month(callback: types.CallbackQuery, state: FSMContext):

    _, month_str, year_str = callback.data.split("_")
    month = int(month_str)
    year = int(year_str)

    await state.update_data(month=month, year=year)

    month_names = [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]

    await callback.message.answer(f"Введите план на {month_names [month -1 ]} {year }:")
    await callback.answer()
    await state.set_state(PlanStates.waiting_plan)


@router.message(PlanStates.waiting_plan)
async def process_plan_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        plan = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Неверный формат числа. Пожалуйста, введите число:")
        return

    store_name = data.get("store_name")
    month = data.get("month")
    year = data.get("year")

    async with get_session() as session:
        store_svc = StoreService(session)
        revenue_svc = RevenueService(session)

        store = await store_svc.get_or_create(store_name)
        success = await revenue_svc.set_monthly_plan(store.id, month, year, plan)

    if success:
        month_names = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь",
        ]

        logger.info(
            "План магазина %s установлен на %s %d: %.2f",
            store.name,
            month_names[month - 1],
            year,
            plan,
        )

        await message.answer(
            f"✅ План магазина {store .name } на {month_names [month -1 ]} {year } установлен: {plan }",
            reply_markup=get_main_keyboard("admin"),
        )
    else:
        await message.answer(
            "❌ Ошибка при установке плана. Попробуйте снова.",
            reply_markup=get_main_keyboard("admin"),
        )

    await state.clear()
