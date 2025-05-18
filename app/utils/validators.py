import re
import logging
from datetime import datetime
from typing import Union, Optional

logger = logging.getLogger(__name__)


def validate_revenue_amount(amount_str: str) -> float:
    """
    Валидирует строку суммы выручки и преобразует её в число.

    Args:
        amount_str: Строка с суммой выручки

    Returns:
        float: Сумма выручки в виде числа с плавающей точкой

    Raises:
        ValueError: Если строка имеет неправильный формат или отрицательное значение
    """
    if not amount_str:
        raise ValueError("Сумма выручки не может быть пустой")

    # Заменяем запятую на точку для корректного парсинга
    amount_str = amount_str.replace(",", ".")

    # Проверяем, что строка содержит число
    if not re.match(r"^[0-9]+(\.[0-9]+)?$", amount_str):
        raise ValueError(
            f"Неверный формат суммы: {amount_str}. Используйте только цифры и точку/запятую."
        )

    # Преобразуем в число
    amount = float(amount_str)

    # Проверяем, что сумма не отрицательная
    if amount < 0:
        raise ValueError("Сумма выручки не может быть отрицательной")

    return amount


def validate_date_format(date_str: str) -> datetime.date:
    """
    Валидирует и преобразует строку даты в объект datetime.date.
    Поддерживает форматы: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD

    Args:
        date_str: Строка с датой

    Returns:
        datetime.date: Объект даты

    Raises:
        ValueError: Если дата имеет неправильный формат
    """
    from app.utils.date_utils import validate_date_format as date_validator

    return date_validator(date_str)


def is_valid_store_name(name: str) -> bool:
    """
    Проверяет, является ли название магазина допустимым.

    Args:
        name: Название магазина для проверки

    Returns:
        bool: True если название допустимо, иначе False
    """
    if not name:
        return False

    # Проверка длины (не более 100 символов)
    if len(name) > 100:
        return False

    # Проверка на SQL-инъекции (простая проверка)
    dangerous_patterns = [
        r"--",
        r"\/\*",
        r"\*\/",
        r";",
        r"DROP",
        r"DELETE",
        r"UPDATE",
        r"INSERT",
        r"SELECT",
        r"UNION",
        r"ALTER",
        r"CREATE",
        r"TRUNCATE",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            logger.warning(
                f"Suspicious store name detected (possible SQL injection): {name}"
            )
            return False

    return True


def is_valid_email(email: str) -> bool:
    """
    Проверяет, является ли строка допустимым email-адресом.

    Args:
        email: Email-адрес для проверки

    Returns:
        bool: True если email допустим, иначе False
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """
    Проверяет, является ли строка допустимым номером телефона.

    Args:
        phone: Номер телефона для проверки

    Returns:
        bool: True если номер телефона допустим, иначе False
    """
    # Очищаем телефон от лишних символов
    clean_phone = re.sub(r"[^\d+]", "", phone)

    # Проверяем разные форматы телефонов
    russian_pattern = r"^\+?7[0-9]{10}$"  # +7XXXXXXXXXX или 7XXXXXXXXXX
    generic_pattern = r"^\+?[0-9]{10,15}$"  # +XXXXXXXXXXX или XXXXXXXXXXX (10-15 цифр)

    return bool(
        re.match(russian_pattern, clean_phone) or re.match(generic_pattern, clean_phone)
    )


def sanitize_input(input_str: str) -> str:
    """
    Санитизирует ввод пользователя для предотвращения инъекций.

    Args:
        input_str: Ввод пользователя

    Returns:
        str: Санитизированная строка
    """
    if not input_str:
        return ""

    # Удаляем потенциально опасные символы
    sanitized = re.sub(r'[<>\'";]', "", input_str)

    # Ограничиваем длину
    return sanitized[:1000]
