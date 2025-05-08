from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.core.config import ADMIN_CHAT_IDS
from app.core.states import AssignStates, CreateStoreStates, CreateManagerStates
from app.core.database import get_session
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.services.revenue_service import RevenueService
from app.utils.menu import get_main_keyboard
from app.utils.matryoshka import create_matryoshka_collection
import logging
import os
from pathlib import Path

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("report"))
async def cmd_report(message: types.Message, state: FSMContext):
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    # Проверяем авторизацию
    user_data = await state.get_data()
    if not user_data.get("user_id"):
        await message.answer("Пожалуйста, сначала авторизуйтесь через /start")
        return

    msg = await message.answer("Генерируется отчет, подождите...")

    # Путь к шаблону матрешки (создаем папку для ресурсов если её нет)
    resources_dir = Path(__file__).parent.parent.parent / "resources"
    resources_dir.mkdir(exist_ok=True)
    template_path = str(resources_dir / "matryoshka_template.png")
    print(template_path)

    # Проверяем, существует ли шаблон матрешки, если нет - создаем простой шаблон
    if not os.path.exists(template_path):
        logger.warning(
            f"Шаблон матрешки не найден по пути: {template_path}, создаем базовый шаблон"
        )
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (300, 500), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        # Рисуем простой контур в виде матрешки
        draw.ellipse((50, 100, 250, 450), outline=(0, 0, 0), width=3)
        img.save(template_path)

    async with get_session() as session:
        service = RevenueService(session)

        # Получаем Excel-отчет для скачивания
        excel_bytes, _ = await service.export_report()

        # Получаем данные для матрешек
        shops_data = await service.get_matryoshka_data()

        # Сортируем магазины по проценту выполнения плана (от большего к меньшему)
        shops_data.sort(key=lambda x: x["fill_percent"], reverse=True)

    # Если нет данных
    if not shops_data:
        await msg.delete()
        await message.answer("Нет данных для построения отчета.")
        return

    # Создаем красивые визуализации с матрешками
    matryoshka_buffers = create_matryoshka_collection(
        template_path, shops_data, layout="vertical", max_per_image=2
    )

    # Отправляем Excel-документ
    await message.answer_document(
        types.BufferedInputFile(excel_bytes, filename="revenue_report.xlsx"),
        caption="Подробный отчет по выручке магазинов",
    )

    # Отправляем каждую группу матрешек как отдельное изображение
    for i, matryoshka_buf in enumerate(matryoshka_buffers, 1):
        # Формируем подпись с общей информацией
        stores_in_image = shops_data[
            (i - 1) * 2 : i * 2
        ]  # Берем две матрешки для текущей группы
        stores_names = ", ".join([s["title"] for s in stores_in_image])

        await message.answer_photo(
            types.BufferedInputFile(
                matryoshka_buf.getvalue(), filename=f"report_matryoshka_{i}.png"
            ),
            caption=f"📊 Выполнение плана: {stores_names}",
        )

    await msg.delete()


@router.message(Command("assign"))
async def cmd_assign_manager(message: types.Message, state: FSMContext):
    """Привязать менеджера к магазину"""
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    # Получаем список всех менеджеров
    async with get_session() as session:
        user_service = UserService(session)
        users = await user_service.get_all_users()

        # Фильтруем только менеджеров
        managers = [u for u in users if u.role == "manager"]

        if not managers:
            await message.answer("В системе нет менеджеров для привязки к магазинам.")
            return

        kb = ReplyKeyboardBuilder()
        for manager in managers:
            kb.button(text=f"{manager.first_name} {manager.last_name}")
        kb.adjust(1)  # По одному в строке для лучшей читаемости

        await message.answer(
            "Выберите менеджера для привязки к магазину:",
            reply_markup=kb.as_markup(resize_keyboard=True),
        )
        await state.set_state(AssignStates.waiting_manager)


@router.message(AssignStates.waiting_manager)
async def process_manager_selection(message: types.Message, state: FSMContext):
    """Обработка выбора менеджера"""
    await state.update_data(selected_manager=message.text)

    # Получаем список магазинов
    async with get_session() as session:
        stores = await StoreService(session).list_stores()

        if not stores:
            await message.answer("В системе нет магазинов для привязки.")
            await state.clear()
            return

        kb = ReplyKeyboardBuilder()
        for store in stores:
            kb.button(text=store.name)
        kb.adjust(2)  # По два в строке

        await message.answer(
            "Выберите магазин для привязки:",
            reply_markup=kb.as_markup(resize_keyboard=True),
        )
        await state.set_state(AssignStates.waiting_store)


@router.message(AssignStates.waiting_store)
async def process_store_selection(message: types.Message, state: FSMContext):
    """Обработка выбора магазина"""
    data = await state.get_data()
    manager_name = data.get("selected_manager", "")
    store_name = message.text

    parts = manager_name.split()
    if len(parts) < 2:
        await message.answer("Ошибка в имени менеджера. Пожалуйста, начните заново.")
        await state.clear()
        return

    first_name, last_name = parts[0], " ".join(parts[1:])

    async with get_session() as session:
        # Получаем менеджера
        user_service = UserService(session)
        manager = await user_service.get_by_name(first_name, last_name)

        if not manager:
            await message.answer(
                f"Менеджер {first_name} {last_name} не найден в системе."
            )
            await state.clear()
            return

        # Получаем магазин
        store_service = StoreService(session)
        store = await store_service.get_or_create(store_name)

        # Привязываем менеджера к магазину
        await user_service.assign_store(manager, store.id)

        logger.info(
            "Менеджер %s %s привязан к магазину %s", first_name, last_name, store_name
        )

        await message.answer(
            f"✅ Менеджер {first_name} {last_name} успешно привязан к магазину {store_name}.",
            reply_markup=get_main_keyboard("admin"),
        )
        await state.clear()


@router.message(Command("users"))
async def cmd_list_users(message: types.Message, state: FSMContext):
    """Просмотр списка пользователей"""
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    async with get_session() as session:
        user_service = UserService(session)
        users = await user_service.get_all_users()

        if not users:
            await message.answer("В системе пока нет пользователей.")
            return

        result = "📋 <b>Список пользователей в системе:</b>\n\n"

        for user in users:
            store_info = (
                f", магазин: {user.store.name}"
                if user.store and user.store.name
                else "без магазина"
            )
            result += (
                f"• {user.first_name} {user.last_name} ({user.role}){store_info}\n"
            )

        await message.answer(result, parse_mode="HTML")


@router.message(Command("stores"))
async def cmd_list_stores(message: types.Message, state: FSMContext):
    """Просмотр списка магазинов и их менеджеров"""
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    async with get_session() as session:
        store_service = StoreService(session)
        stores = await store_service.list_stores()

        if not stores:
            await message.answer("В системе пока нет магазинов.")
            return

        result = "🏪 <b>Список магазинов в системе:</b>\n\n"

        for store in stores:
            managers = (
                ", ".join([f"{m.first_name} {m.last_name}" for m in store.managers])
                if store.managers
                else "нет"
            )
            result += f"• <b>{store.name}</b> (план: {store.plan})\n  Менеджеры: {managers}\n\n"

        await message.answer(result, parse_mode="HTML")


@router.message(Command("addstore"))
async def cmd_add_store(message: types.Message, state: FSMContext):
    """Добавление нового магазина"""
    # Сброс состояния перед началом
    await state.clear()
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    await message.answer(
        "Введите название нового магазина:", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CreateStoreStates.waiting_name)


@router.message(CreateStoreStates.waiting_name)
async def process_store_name(message: types.Message, state: FSMContext):
    """Обработка ввода названия магазина"""
    store_name = message.text.strip()

    if not store_name:
        await message.answer(
            "Название магазина не может быть пустым. Пожалуйста, введите название:"
        )
        return

    # Сохраняем название магазина в состояние
    await state.update_data(store_name=store_name)

    # Явно устанавливаем состояние перед отправкой сообщения
    await state.set_state(CreateStoreStates.waiting_plan)

    # Запрашиваем план для нового магазина
    await message.answer("Введите план для магазина (число):")


@router.message(CreateStoreStates.waiting_plan)
async def process_store_plan(message: types.Message, state: FSMContext):
    """Обработка ввода плана магазина"""
    try:
        plan = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Неверный формат числа. Пожалуйста, введите число:")
        return

    data = await state.get_data()
    store_name = data.get("store_name")

    async with get_session() as session:
        store_service = StoreService(session)
        # Проверяем, существует ли уже магазин с таким названием
        existing_store = await store_service.get_by_name(store_name)

        if existing_store:
            await message.answer(
                f"Магазин '{store_name}' уже существует. План обновлен.",
                reply_markup=get_main_keyboard("admin"),
            )
            await store_service.set_plan(existing_store, plan)
        else:
            store = await store_service.get_or_create(store_name)
            await store_service.set_plan(store, plan)
            await message.answer(
                f"✅ Новый магазин '{store_name}' успешно добавлен с планом {plan}.",
                reply_markup=get_main_keyboard("admin"),
            )

    await state.clear()


@router.message(Command("addmanager"))
async def cmd_add_manager(message: types.Message, state: FSMContext):
    """Добавление нового менеджера"""
    # Сброс состояния перед началом
    await state.clear()
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    await message.answer(
        "Введите имя нового менеджера:", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CreateManagerStates.waiting_first_name)


@router.message(CreateManagerStates.waiting_first_name)
async def process_manager_first_name(message: types.Message, state: FSMContext):
    """Обработка ввода имени менеджера"""
    first_name = message.text.strip()

    if not first_name:
        await message.answer("Имя не может быть пустым. Пожалуйста, введите имя:")
        return

    await state.update_data(first_name=first_name)
    await message.answer("Введите фамилию менеджера:")
    await state.set_state(CreateManagerStates.waiting_last_name)


@router.message(CreateManagerStates.waiting_last_name)
async def process_manager_last_name(message: types.Message, state: FSMContext):
    """Обработка ввода фамилии менеджера"""
    last_name = message.text.strip()

    if not last_name:
        await message.answer(
            "Фамилия не может быть пустой. Пожалуйста, введите фамилию:"
        )
        return

    await state.update_data(last_name=last_name)

    # Запрашиваем магазин для привязки
    async with get_session() as session:
        stores = await StoreService(session).list_stores()

    if not stores:
        await message.answer(
            "⚠️ В системе нет магазинов. Сначала добавьте магазин с помощью команды /addstore.",
            reply_markup=get_main_keyboard("admin"),
        )
        await state.clear()
        return

    # Создаем клавиатуру с магазинами
    kb = ReplyKeyboardBuilder()

    # Добавляем опцию "Не привязывать" в начало
    kb.button(text="Без привязки")

    # Добавляем все магазины
    for store in stores:
        kb.button(text=store.name)
    kb.adjust(2)  # По 2 кнопки в строке

    await message.answer(
        "Выберите магазин для привязки менеджера (или выберите 'Без привязки'):",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
    await state.set_state(CreateManagerStates.waiting_store)


@router.message(CreateManagerStates.waiting_store)
async def process_manager_store(message: types.Message, state: FSMContext):
    """Обработка выбора магазина для менеджера"""
    data = await state.get_data()
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    store_name = message.text

    store_id = None

    async with get_session() as session:
        user_service = UserService(session)

        # Проверяем, существует ли уже менеджер с таким именем
        existing_user = await user_service.get_by_name(first_name, last_name)

        if existing_user:
            await message.answer(
                f"⚠️ Пользователь с именем {first_name} {last_name} уже существует в системе.",
                reply_markup=get_main_keyboard("admin"),
            )
            await state.clear()
            return

        # Если выбран магазин, получаем его ID
        if store_name != "Без привязки":
            store_service = StoreService(session)
            store = await store_service.get_by_name(store_name)
            if store:
                store_id = store.id

        # Создаем менеджера
        user = await user_service.get_or_create(
            first_name, last_name, "manager", store_id
        )

        store_info = (
            f", привязан к магазину: {store_name}"
            if store_id
            else ", без привязки к магазину"
        )
        await message.answer(
            f"✅ Менеджер {first_name} {last_name} успешно добавлен{store_info}.",
            reply_markup=get_main_keyboard("admin"),
        )

    logger.info(
        f"Создан новый менеджер: {first_name} {last_name}, магазин: {store_name}"
    )
    await state.clear()
