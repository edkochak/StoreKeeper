from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import date, datetime, timedelta
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.core.states import RevenueStates
from app.core.database import get_session
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.services.revenue_service import RevenueService
from app.utils.menu import get_main_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("revenue"))
async def cmd_revenue(message: types.Message, state: FSMContext):
    # Проверяем авторизацию
    user_data = await state.get_data()
    if not user_data.get("user_id"):
        await message.answer("Пожалуйста, сначала авторизуйтесь через /start")
        return

    # Формируем клавиатуру с выбором даты
    kb = ReplyKeyboardBuilder()
    today = date.today()

    # Сегодня и последние 7 дней
    for i in range(8):
        day = today - timedelta(days=i)
        day_str = day.strftime("%d.%m.%Y")
        kb.button(text=day_str)

    # Размещаем по 2 кнопки в ряду
    kb.adjust(2)

    await message.answer(
        "Выберите дату для ввода выручки:",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
    await state.set_state(RevenueStates.waiting_date)


@router.message(RevenueStates.waiting_date)
async def process_date(message: types.Message, state: FSMContext):
    try:
        # Пробуем распарсить дату
        selected_date = datetime.strptime(message.text, "%d.%m.%Y").date()

        # Проверка, что дата не из будущего
        if selected_date > date.today():
            await message.answer(
                "Нельзя вводить выручку за будущие даты. Выберите другую дату:"
            )
            return

        # Сохраняем дату в состояние
        await state.update_data(selected_date=selected_date.isoformat())

        # Получаем данные пользователя
        user_data = await state.get_data()
        user_id = user_data.get("user_id")

        # Получаем информацию о магазине менеджера
        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_by_name(
                user_data.get("first_name", ""), user_data.get("last_name", "")
            )

            # Если менеджер привязан к магазину
            if user and user.store_id:
                # Сразу переходим к вводу суммы
                store_service = StoreService(session)
                store = await store_service.get_by_id(user.store_id)

                if store:
                    await state.update_data(store_id=store.id, store_name=store.name)
                    await message.answer(
                        f"Введите выручку за {message.text} для магазина {store.name}:"
                    )
                    await state.set_state(RevenueStates.waiting_amount)
                    return

            # Если нет привязки к магазину или админ
            stores = await StoreService(session).list_stores()

        # Если нет магазинов или пользователь - админ (может выбирать магазин)
        kb = ReplyKeyboardBuilder()
        for store in stores:
            kb.button(text=store.name)
        kb.adjust(2)

        await message.answer(
            "Выберите магазин:", reply_markup=kb.as_markup(resize_keyboard=True)
        )
        await state.set_state(RevenueStates.waiting_store)
    except ValueError:
        await message.answer("Неверный формат даты. Используйте формат ДД.ММ.ГГГГ:")


@router.message(RevenueStates.waiting_store)
async def process_store(message: types.Message, state: FSMContext):
    await state.update_data(store_name=message.text)
    await message.answer("Введите выручку за выбранную дату числом:")
    await state.set_state(RevenueStates.waiting_amount)


@router.message(RevenueStates.waiting_amount)
async def process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 0:
            await message.answer(
                "Выручка не может быть отрицательной. Введите положительное число:"
            )
            return
    except ValueError:
        await message.answer("Неверный формат числа. Пожалуйста, введите число:")
        return

    store_name = data.get("store_name")
    selected_date = data.get("selected_date")
    user_id = data.get("user_id")

    if not selected_date:
        # Если каким-то образом дата не была сохранена, используем текущую
        logger.warning("Дата не найдена в состоянии, используем текущую")
        selected_date = date.today().isoformat()

    logger.info(
        "Обработка выручки: магазин=%s, дата=%s, сумма=%.2f",
        store_name,
        selected_date,
        amount,
    )

    revenue_date = date.fromisoformat(selected_date)

    async with get_session() as session:
        store_service = StoreService(session)
        store = await store_service.get_or_create(store_name)

        revenue_service = RevenueService(session)
        revenue = await revenue_service.create_revenue(
            amount, store.id, user_id, revenue_date
        )

    logger.info(
        "Результат сохранения выручки: магазин=%s, дата=%s, сумма=%.2f",
        store_name,
        revenue_date,
        amount,
    )

    await message.answer(
        f"✅ Выручка {amount} для магазина {store_name} за {revenue_date.strftime('%d.%m.%Y')} успешно сохранена.",
        reply_markup=get_main_keyboard(data.get("role")),
    )
    # Завершаем FSM, очищаем только состояние, сохраняем данные пользователя
    await state.set_state(None)


@router.message(Command("status"))
async def cmd_status(message: types.Message, state: FSMContext):
    """Показывает статус выполнения плана для менеджера"""
    user_data = await state.get_data()
    if not user_data.get("user_id"):
        await message.answer("Пожалуйста, сначала авторизуйтесь через /start")
        return

    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_by_name(
            user_data.get("first_name", ""), user_data.get("last_name", "")
        )

        if not user or not user.store_id:
            await message.answer("У вас нет привязки к магазину.")
            return

        store_service = StoreService(session)
        store = await store_service.get_by_id(user.store_id)

        revenue_service = RevenueService(session)
        current_month_total = await revenue_service.get_month_total(store.id)

        plan_progress = 0
        if store.plan > 0:
            plan_progress = (current_month_total / store.plan) * 100

        await message.answer(
            f"📊 Статус выполнения плана для магазина {store.name}:\n\n"
            f"План на месяц: {store.plan}\n"
            f"Текущая выручка: {current_month_total}\n"
            f"Процент выполнения: {plan_progress:.1f}%"
        )
