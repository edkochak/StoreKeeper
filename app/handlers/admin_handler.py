from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.core.config import ADMIN_CHAT_IDS
from app.core.states import (
    AssignStates,
    CreateStoreStates,
    CreateManagerStates,
    EditStoreStates,
    EditManagerStates,
    EditRevenueStates,
)
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

    await state.clear()

    msg = await message.answer("Генерируется отчет, подождите...")

    resources_dir = Path(__file__).parent.parent.parent / "resources"
    resources_dir.mkdir(exist_ok=True)
    template_path = str(resources_dir / "matryoshka_template.png")
    print(template_path)

    if not os.path.exists(template_path):
        logger.warning(
            f"Шаблон матрешки не найден по пути: {template_path }, создаем базовый шаблон"
        )
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (300, 500), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        draw.ellipse((50, 100, 250, 450), outline=(0, 0, 0), width=3)
        img.save(template_path)

    async with get_session() as session:
        service = RevenueService(session)

        excel_bytes, _ = await service.export_report()

        shops_data = await service.get_matryoshka_data()

        shops_data.sort(key=lambda x: x["fill_percent"], reverse=True)

    if not shops_data:
        await msg.delete()
        await message.answer("Нет данных для построения отчета.")
        return

    matryoshka_buffers = create_matryoshka_collection(
        template_path, shops_data, layout="vertical", max_per_image=2
    )

    await message.answer_document(
        types.BufferedInputFile(excel_bytes, filename="revenue_report.xlsx"),
        caption="Подробный отчет по выручке магазинов",
    )

    for i, matryoshka_buf in enumerate(matryoshka_buffers, 1):

        stores_in_image = shops_data[(i - 1) * 2 : i * 2]
        stores_names = ", ".join([s["title"] for s in stores_in_image])

        await message.answer_photo(
            types.BufferedInputFile(
                matryoshka_buf.getvalue(), filename=f"report_matryoshka_{i }.png"
            ),
            caption=f"📊 Выполнение плана: {stores_names }",
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

    await state.clear()

    async with get_session() as session:
        user_service = UserService(session)
        users = await user_service.get_all_users()

        managers = [u for u in users if u.role == "manager"]

        if not managers:
            await message.answer("В системе нет менеджеров для привязки к магазинам.")
            return

        kb = ReplyKeyboardBuilder()
        for manager in managers:
            kb.button(text=f"{manager .first_name } {manager .last_name }")
        kb.adjust(1)

        await message.answer(
            "Выберите менеджера для привязки к магазину:",
            reply_markup=kb.as_markup(resize_keyboard=True),
        )
        await state.set_state(AssignStates.waiting_manager)


@router.message(AssignStates.waiting_manager)
async def process_manager_selection(message: types.Message, state: FSMContext):
    """Обработка выбора менеджера"""
    await state.update_data(selected_manager=message.text)

    async with get_session() as session:
        stores = await StoreService(session).list_stores()

        if not stores:
            await message.answer("В системе нет магазинов для привязки.")
            await state.clear()
            return

        kb = ReplyKeyboardBuilder()
        for store in stores:
            kb.button(text=store.name)
        kb.adjust(2)

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

        user_service = UserService(session)
        manager = await user_service.get_by_name(first_name, last_name)

        if not manager:
            await message.answer(
                f"Менеджер {first_name } {last_name } не найден в системе."
            )
            await state.clear()
            return

        store_service = StoreService(session)
        store = await store_service.get_or_create(store_name)

        await user_service.assign_store(manager, store.id)

        logger.info(
            "Менеджер %s %s привязан к магазину %s", first_name, last_name, store_name
        )

        await message.answer(
            f"✅ Менеджер {first_name } {last_name } успешно привязан к магазину {store_name }.",
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
                f", магазин: {user .store .name }"
                if user.store and user.store.name
                else "без магазина"
            )
            result += f"• {user .first_name } {user .last_name } ({user .role }){store_info }\n"

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
                ", ".join([f"{m .first_name } {m .last_name }" for m in store.managers])
                if store.managers
                else "нет"
            )
            result += f"• <b>{store .name }</b> (план: {store .plan })\n  Менеджеры: {managers }\n\n"

        await message.answer(result, parse_mode="HTML")


@router.message(Command("addstore"))
async def cmd_add_store(message: types.Message, state: FSMContext):
    """Добавление нового магазина"""

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

    await state.update_data(store_name=store_name)

    await state.set_state(CreateStoreStates.waiting_plan)

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

        existing_store = await store_service.get_by_name(store_name)

        if existing_store:
            await message.answer(
                f"Магазин '{store_name }' уже существует. План обновлен.",
                reply_markup=get_main_keyboard("admin"),
            )
            await store_service.set_plan(existing_store, plan)
        else:
            store = await store_service.get_or_create(store_name)
            await store_service.set_plan(store, plan)
            await message.answer(
                f"✅ Новый магазин '{store_name }' успешно добавлен с планом {plan }.",
                reply_markup=get_main_keyboard("admin"),
            )

    await state.clear()


@router.message(Command("addmanager"))
async def cmd_add_manager(message: types.Message, state: FSMContext):
    """Добавление нового менеджера"""

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

    async with get_session() as session:
        stores = await StoreService(session).list_stores()

    if not stores:
        await message.answer(
            "⚠️ В системе нет магазинов. Сначала добавьте магазин с помощью команды /addstore.",
            reply_markup=get_main_keyboard("admin"),
        )
        await state.clear()
        return

    kb = ReplyKeyboardBuilder()

    kb.button(text="Без привязки")

    for store in stores:
        kb.button(text=store.name)
    kb.adjust(2)

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

        existing_user = await user_service.get_by_name(first_name, last_name)

        if existing_user:
            await message.answer(
                f"⚠️ Пользователь с именем {first_name } {last_name } уже существует в системе.",
                reply_markup=get_main_keyboard("admin"),
            )
            await state.clear()
            return

        if store_name != "Без привязки":
            store_service = StoreService(session)
            store = await store_service.get_by_name(store_name)
            if store:
                store_id = store.id

        user = await user_service.get_or_create(
            first_name, last_name, "manager", store_id
        )

        store_info = (
            f", привязан к магазину: {store_name }"
            if store_id
            else ", без привязки к магазину"
        )
        await message.answer(
            f"✅ Менеджер {first_name } {last_name } успешно добавлен{store_info }.",
            reply_markup=get_main_keyboard("admin"),
        )

    logger.info(
        f"Создан новый менеджер: {first_name } {last_name }, магазин: {store_name }"
    )
    await state.clear()


@router.message(Command("editstore"))
async def cmd_edit_store(message: types.Message, state: FSMContext):
    """Редактирование существующего магазина"""

    await state.clear()

    async with get_session() as session:
        stores = await StoreService(session).list_stores()

        if not stores:
            await message.answer("В системе пока нет магазинов для редактирования.")
            return

        kb = ReplyKeyboardBuilder()
        for store in stores:
            kb.button(text=store.name)
        kb.adjust(2)

        await message.answer(
            "Выберите магазин для редактирования:",
            reply_markup=kb.as_markup(resize_keyboard=True),
        )
        await state.set_state(EditStoreStates.waiting_store)


@router.message(EditStoreStates.waiting_store)
async def process_edit_store_selection(message: types.Message, state: FSMContext):
    """Обработка выбора магазина для редактирования"""
    store_name = message.text.strip()
    await state.update_data(store_name=store_name)

    await message.answer(
        f"Выберите, что хотите изменить для магазина '{store_name }':",
        reply_markup=get_edit_store_field_keyboard(),
    )
    await state.set_state(EditStoreStates.waiting_field)


def get_edit_store_field_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Изменить название")
    kb.button(text="Изменить план")
    kb.button(text="Удалить магазин")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


@router.message(EditStoreStates.waiting_field)
async def process_edit_store_field(message: types.Message, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    field = message.text.strip()
    data = await state.get_data()
    store_name = data.get("store_name")

    if field == "Удалить магазин":
        async with get_session() as session:
            store_service = StoreService(session)
            store = await store_service.get_by_name(store_name)
            if store:
                await store_service.delete_store(store)
                await message.answer(f"Магазин '{store_name }' удален.")
            else:
                await message.answer(f"Магазин '{store_name }' не найден.")
        await state.clear()
        return

    if field == "Изменить название":
        await state.update_data(edit_field="name")
        await message.answer(
            "Введите новое название магазина:", reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(EditStoreStates.waiting_value)
    elif field == "Изменить план":
        await state.update_data(edit_field="plan")
        await message.answer(
            "Введите новый план для магазина (число):",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await state.set_state(EditStoreStates.waiting_value)
    else:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
        return


@router.message(EditStoreStates.waiting_value)
async def process_edit_store_value(message: types.Message, state: FSMContext):
    """Обработка ввода нового значения для редактирования"""
    data = await state.get_data()
    store_name = data.get("store_name")
    edit_field = data.get("edit_field")
    new_value = message.text.strip()

    async with get_session() as session:
        store_service = StoreService(session)
        store = await store_service.get_by_name(store_name)

        if not store:
            await message.answer(
                f"Магазин '{store_name }' не найден.",
                reply_markup=get_main_keyboard("admin"),
            )
            await state.clear()
            return

        if edit_field == "name":

            existing_store = await store_service.get_by_name(new_value)
            if existing_store and existing_store.id != store.id:
                await message.answer(
                    f"Магазин с названием '{new_value }' уже существует. Пожалуйста, выберите другое название.",
                    reply_markup=get_main_keyboard("admin"),
                )
                return

            updated_store = await store_service.update_name(store, new_value)
            await message.answer(
                f"✅ Название магазина успешно изменено на '{new_value }'.",
                reply_markup=get_main_keyboard("admin"),
            )
        elif edit_field == "plan":
            try:
                new_plan = float(new_value.replace(",", "."))
                if new_plan < 0:
                    await message.answer(
                        "План не может быть отрицательным. Пожалуйста, введите положительное число.",
                        reply_markup=get_main_keyboard("admin"),
                    )
                    return

                updated_store = await store_service.set_plan(store, new_plan)
                await message.answer(
                    f"✅ План магазина '{store_name }' обновлён до {new_plan }.",
                    reply_markup=get_main_keyboard("admin"),
                )
            except ValueError:
                await message.answer(
                    "Неверный формат числа. Пожалуйста, введите число.",
                    reply_markup=get_main_keyboard("admin"),
                )
                return

    await state.clear()


@router.message(Command("editmanager"))
async def cmd_edit_manager(message: types.Message, state: FSMContext):
    """Редактирование существующего менеджера"""
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    await state.clear()

    async with get_session() as session:
        user_service = UserService(session)
        users = await user_service.get_all_users()

        managers = [u for u in users if u.role == "manager"]

        if not managers:
            await message.answer("В системе пока нет менеджеров для редактирования.")
            return

        kb = ReplyKeyboardBuilder()
        for manager in managers:
            kb.button(text=f"{manager .first_name } {manager .last_name }")
        kb.adjust(1)

        await message.answer(
            "Выберите менеджера для редактирования:",
            reply_markup=kb.as_markup(resize_keyboard=True),
        )
        await state.set_state(EditManagerStates.waiting_manager)


def get_edit_manager_field_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Изменить имя")
    kb.button(text="Изменить фамилию")
    kb.button(text="Изменить магазин")
    kb.button(text="Удалить менеджера")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


@router.message(EditManagerStates.waiting_manager)
async def process_edit_manager_selection(message: types.Message, state: FSMContext):
    """
    Обработка выбора менеджера для редактирования.
    """
    manager_name_raw = message.text.strip()

    parts = manager_name_raw.split(" ", 1)
    if len(parts) < 2:
        await message.answer(
            "Пожалуйста, укажите имя и фамилию (фамилия может содержать несколько слов).",
            reply_markup=get_main_keyboard("admin"),
        )
        await state.clear()
        return

    await state.update_data(manager_name=manager_name_raw)
    await state.set_state(EditManagerStates.waiting_field)
    await message.answer(
        f"Выберите, что хотите изменить для менеджера '{manager_name_raw }':",
        reply_markup=get_edit_manager_field_keyboard(),
    )


@router.message(EditManagerStates.waiting_field)
async def process_edit_manager_field(message: types.Message, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    field = message.text.strip()
    data = await state.get_data()
    manager_name = data.get("manager_name")

    parts = manager_name.split(" ", 1)
    if len(parts) < 2:
        await message.answer(
            "Ошибка в имени менеджера. Пожалуйста, начните заново.",
            reply_markup=get_main_keyboard("admin"),
        )
        await state.clear()
        return

    first_name, last_name = parts[0], parts[1]
    logger.info(f"Разбор имени менеджера: имя='{first_name }', фамилия='{last_name }'")

    if field == "Изменить имя":
        await state.update_data(
            edit_field="first_name", first_name=first_name, last_name=last_name
        )
        await message.answer(
            "Введите новое имя менеджера:", reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(EditManagerStates.waiting_value)
    elif field == "Изменить фамилию":
        await state.update_data(
            edit_field="last_name", first_name=first_name, last_name=last_name
        )
        await message.answer(
            "Введите новую фамилию менеджера:", reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(EditManagerStates.waiting_value)
    elif field == "Изменить магазин":
        data = await state.get_data()
        full_name = data.get("manager_name", "")
        parts = full_name.split(" ", 1)
        if len(parts) == 2:
            first_name, last_name = parts
            async with get_session() as session:
                user_svc = UserService(session)
                manager = await user_svc.get_by_name_with_store(first_name, last_name)

        await state.update_data(
            edit_field="store", first_name=first_name, last_name=last_name
        )

        async with get_session() as session:
            stores = await StoreService(session).list_stores()

            if not stores:
                await message.answer(
                    "В системе нет магазинов для привязки.",
                    reply_markup=get_main_keyboard("admin"),
                )
                await state.clear()
                return

            kb = ReplyKeyboardBuilder()

            kb.button(text="Без привязки")

            for store in stores:
                kb.button(text=store.name)
            kb.adjust(2)

            await message.answer(
                "Выберите новый магазин для менеджера (или 'Без привязки'):",
                reply_markup=kb.as_markup(resize_keyboard=True),
            )
            await state.set_state(EditManagerStates.waiting_value)
    elif field == "Удалить менеджера":
        async with get_session() as session:
            user_service = UserService(session)
            manager = await user_service.get_by_name(first_name, last_name)
            if manager:
                await user_service.delete_user(manager)
                await message.answer(f"Менеджер '{manager_name }' удален.")
            else:
                await message.answer(f"Менеджер '{manager_name }' не найден.")
        await state.clear()
        return
    else:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
        return


@router.message(EditManagerStates.waiting_value)
async def process_edit_manager_value(message: types.Message, state: FSMContext):
    """Обработка ввода нового значения для редактирования"""
    data = await state.get_data()
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    edit_field = data.get("edit_field")
    new_value = message.text.strip()

    async with get_session() as session:
        user_service = UserService(session)

        logger.info(f"Поиск менеджера: имя='{first_name }', фамилия='{last_name }'")

        manager = await user_service.get_by_name(first_name, last_name)

        if not manager:
            await message.answer(
                f"Менеджер '{first_name } {last_name }' не найден. Проверьте правильность имени и фамилии.",
                reply_markup=get_main_keyboard("admin"),
            )
            await state.clear()
            return

        if edit_field == "first_name":
            if not new_value:
                await message.answer(
                    "Имя не может быть пустым. Пожалуйста, введите имя.",
                    reply_markup=get_main_keyboard("admin"),
                )
                return

            updated_manager = await user_service.update_first_name(manager, new_value)
            await message.answer(
                f"✅ Имя менеджера изменено с '{first_name }' на '{new_value }'.",
                reply_markup=get_main_keyboard("admin"),
            )

        elif edit_field == "last_name":
            if not new_value:
                await message.answer(
                    "Фамилия не может быть пустой. Пожалуйста, введите фамилию.",
                    reply_markup=get_main_keyboard("admin"),
                )
                return

            updated_manager = await user_service.update_last_name(manager, new_value)
            await message.answer(
                f"✅ Фамилия менеджера изменена с '{last_name }' на '{new_value }'.",
                reply_markup=get_main_keyboard("admin"),
            )

        elif edit_field == "store":
            if new_value == "Без привязки":
                updated_manager = await user_service.assign_store(manager, None)
                await message.answer(
                    f"✅ Менеджер '{first_name } {last_name }' больше не привязан к магазину.",
                    reply_markup=get_main_keyboard("admin"),
                )
            else:
                store_service = StoreService(session)
                store = await store_service.get_by_name(new_value)

                if not store:
                    await message.answer(
                        f"Магазин '{new_value }' не найден.",
                        reply_markup=get_main_keyboard("admin"),
                    )
                    await state.clear()
                    return

                updated_manager = await user_service.assign_store(manager, store.id)
                await message.answer(
                    f"✅ Менеджер '{first_name } {last_name }' теперь привязан к магазину '{new_value }'.",
                    reply_markup=get_main_keyboard("admin"),
                )

    await state.clear()


@router.message(Command("editrevenue"))
async def cmd_edit_revenue(message: types.Message, state: FSMContext):
    """Корректировка выручки любого магазина за любой день администратором"""
    if message.chat.id not in ADMIN_CHAT_IDS:
        await message.answer(
            "У вас нет прав администратора для выполнения этой команды."
        )
        return

    await state.clear()

    async with get_session() as session:
        stores = await StoreService(session).list_stores()

    if not stores:
        await message.answer("В системе нет магазинов.")
        return

    kb = ReplyKeyboardBuilder()
    for store in stores:
        kb.button(text=store.name)
    kb.adjust(2)

    await message.answer(
        "Выберите магазин для корректировки выручки:",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
    await state.set_state(EditRevenueStates.waiting_store)


@router.message(EditRevenueStates.waiting_store)
async def process_edit_revenue_store(message: types.Message, state: FSMContext):
    """Обработка выбора магазина для корректировки выручки"""
    store_name = message.text

    async with get_session() as session:
        store_service = StoreService(session)
        store = await store_service.get_by_name(store_name)

        if not store:
            await message.answer("Магазин не найден. Выберите магазин из списка выше.")
            return

    await state.update_data(store_id=store.id, store_name=store_name)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    import datetime

    kb = InlineKeyboardBuilder()
    today = datetime.date.today()

    for i in range(30):
        date_obj = today - datetime.timedelta(days=i)
        button_text = date_obj.strftime("%d.%m.%Y")
        callback_data = f"editrev_date_{date_obj .isoformat ()}"
        kb.button(text=button_text, callback_data=callback_data)

    kb.adjust(5)

    await message.answer(
        f"Выберите дату для корректировки выручки магазина {store_name }:",
        reply_markup=kb.as_markup(),
    )
    await state.set_state(EditRevenueStates.waiting_date)


@router.message(EditRevenueStates.waiting_date)
async def process_edit_revenue_date_message(message: types.Message, state: FSMContext):
    """Альтернативный обработчик выбора даты через обычное сообщение (для тестов)"""
    from datetime import datetime

    try:

        date_obj = datetime.strptime(message.text, "%d.%m.%Y").date()
        date_str = date_obj.isoformat()
    except ValueError:
        try:

            date_obj = datetime.fromisoformat(message.text).date()
            date_str = date_obj.isoformat()
        except ValueError:
            await message.answer("Неверный формат даты. Используйте формат ДД.ММ.ГГГГ")
            return

    await state.update_data(revenue_date=date_str, selected_date=date_str)

    data = await state.get_data()
    store_name = data.get("store_name")
    store_id = data.get("store_id")

    revenue_date = date_obj

    async with get_session() as session:
        revenue_service = RevenueService(session)
        existing_revenue = await revenue_service.get_revenue(store_id, revenue_date)

        if existing_revenue:
            current_amount = existing_revenue.amount
            await message.answer(
                f"Текущая выручка магазина {store_name } за {revenue_date .strftime ('%d.%m.%Y')}: {current_amount }\n\n"
                f"Введите новую сумму выручки:"
            )
            await state.update_data(revenue_id=existing_revenue.id)
        else:
            await message.answer(
                f"За {revenue_date .strftime ('%d.%m.%Y')} выручка для магазина {store_name } не найдена.\n\n"
                f"Введите сумму выручки для создания новой записи:"
            )

    await state.set_state(EditRevenueStates.waiting_amount)


@router.callback_query(EditRevenueStates.waiting_date)
async def process_edit_revenue_date(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора даты для корректировки выручки"""

    date_str = callback.data.replace("editrev_date_", "")

    await state.update_data(revenue_date=date_str, selected_date=date_str)

    data = await state.get_data()
    store_name = data.get("store_name")
    store_id = data.get("store_id")

    from datetime import datetime

    revenue_date = datetime.fromisoformat(date_str).date()

    async with get_session() as session:
        revenue_service = RevenueService(session)
        existing_revenue = await revenue_service.get_revenue(store_id, revenue_date)

        if existing_revenue:
            current_amount = existing_revenue.amount
            await callback.message.answer(
                f"Текущая выручка магазина {store_name } за {revenue_date .strftime ('%d.%m.%Y')}: {current_amount }\n\n"
                f"Введите новую сумму выручки:"
            )
            await state.update_data(revenue_id=existing_revenue.id)
        else:
            await callback.message.answer(
                f"За {revenue_date .strftime ('%d.%m.%Y')} выручка для магазина {store_name } не найдена.\n\n"
                f"Введите сумму выручки для создания новой записи:"
            )

    await callback.answer()
    await state.set_state(EditRevenueStates.waiting_amount)


@router.message(EditRevenueStates.waiting_amount)
async def process_edit_revenue_amount(message: types.Message, state: FSMContext):
    """Обработка ввода новой суммы выручки"""
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 0:
            await message.answer(
                "Сумма выручки не может быть отрицательной. Введите корректную сумму:"
            )
            return
    except ValueError:
        await message.answer("Неверный формат числа. Пожалуйста, введите число:")
        return

    data = await state.get_data()
    store_id = data.get("store_id")
    store_name = data.get("store_name")
    revenue_date_str = data.get("revenue_date")
    revenue_id = data.get("revenue_id")

    from datetime import datetime

    revenue_date = datetime.fromisoformat(revenue_date_str).date()

    async with get_session() as session:
        revenue_service = RevenueService(session)

        if revenue_id:

            success = await revenue_service.update_revenue(revenue_id, amount)
            action = "обновлена"
        else:

            user_service = UserService(session)

            managers = await user_service.get_by_store_id(store_id)
            if managers:
                manager_id = managers[0].id
            else:

                system_manager = await user_service.get_or_create(
                    "Система", "Администратор", "manager", store_id=store_id
                )
                manager_id = system_manager.id

            revenue = await revenue_service.create_revenue(
                amount, store_id, manager_id, revenue_date
            )
            success = revenue is not None
            action = "создана"

        if success:
            logger.info(
                f"Администратор {message .from_user .id } {action } выручку для магазина {store_name } "
                f"на {revenue_date }: {amount }"
            )

            await message.answer(
                f"✅ Выручка магазина {store_name } за {revenue_date .strftime ('%d.%m.%Y')} {action }: {amount }",
                reply_markup=get_main_keyboard("admin"),
            )
        else:
            await message.answer(
                f"❌ Ошибка при изменении выручки. Попробуйте снова.",
                reply_markup=get_main_keyboard("admin"),
            )

    await state.clear()
