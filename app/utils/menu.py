from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder

ADMIN_MENU_TEXT = """
📊 <b>Меню администратора</b>
  
Доступные команды:
/report - Выгрузить отчет в Excel с графиками выполнения плана
/setplan - Установить план для магазина
/assign - Привязать менеджера к магазину
/addstore - Добавить новый магазин
/addmanager - Добавить нового менеджера
/users - Показать всех пользователей
/stores - Показать все магазины
/help - Показать это сообщение

Администратор имеет доступ к управлению всеми магазинами и отчетам.
"""

MANAGER_MENU_TEXT = """
🏪 <b>Меню менеджера магазина</b>

Доступные команды:
/revenue - Ввести выручку за определенную дату
/status - Показать статус выполнения плана
/help - Показать это сообщение

Менеджер может вносить данные по выручке только для своего магазина.
"""

GUEST_MENU_TEXT = """
👋 <b>Меню гостя</b>

Для начала работы с ботом необходимо авторизоваться.
Доступные команды:
/start - Авторизоваться в системе
/help - Показать это сообщение

Введите свои имя и фамилию, чтобы войти в систему.
"""


def get_main_keyboard(role: str = None):
    """Создает клавиатуру в зависимости от роли пользователя"""
    builder = ReplyKeyboardBuilder()

    if role == "admin":
        builder.row(
            types.KeyboardButton(text="/report"), types.KeyboardButton(text="/setplan")
        )
        builder.row(
            types.KeyboardButton(text="/addstore"),
            types.KeyboardButton(text="/addmanager"),
        )
        builder.row(
            types.KeyboardButton(text="/assign"), types.KeyboardButton(text="/users")
        )
        builder.row(
            types.KeyboardButton(text="/stores"), types.KeyboardButton(text="/help")
        )
    elif role == "manager":
        builder.row(
            types.KeyboardButton(text="/revenue"), types.KeyboardButton(text="/status")
        )
        builder.row(types.KeyboardButton(text="/help"))
    else:
        builder.row(
            types.KeyboardButton(text="/start"), types.KeyboardButton(text="/help")
        )

    return builder.as_markup(resize_keyboard=True)


def get_menu_text(role: str = None):
    """Возвращает текст меню в зависимости от роли пользователя"""
    if role == "admin":
        return ADMIN_MENU_TEXT
    elif role == "manager":
        return MANAGER_MENU_TEXT
    else:
        return GUEST_MENU_TEXT
