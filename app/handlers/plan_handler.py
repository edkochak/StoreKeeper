from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.core.config import ADMIN_CHAT_IDS
from app.core.states import PlanStates
from app.core.database import get_session
from app.services.store_service import StoreService
from app.utils.menu import get_main_keyboard
import logging

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
    await message.answer("Введите новый план числом:")
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
    async with get_session() as session:
        svc = StoreService(session)
        store = await svc.get_or_create(store_name)
        updated = await svc.set_plan(store, plan)
    logger.info("План магазина %s установлен: %.2f", updated.name, updated.plan)

    await message.answer(
        f"✅ План магазина {updated .name } обновлён до {updated .plan }.",
        reply_markup=get_main_keyboard("admin"),
    )
    await state.clear()
