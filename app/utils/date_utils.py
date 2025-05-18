import calendar
import datetime
from typing import Tuple, Optional


def get_month_range(date_obj: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """
    Возвращает первый и последний день месяца.

    Args:
        date_obj: Дата, для которой нужно определить диапазон месяца

    Returns:
        Tuple[datetime.date, datetime.date]: Кортеж из первого и последнего дня месяца
    """
    year = date_obj.year
    month = date_obj.month

    first_day = datetime.date(year, month, 1)

    _, last_day_of_month = calendar.monthrange(year, month)
    last_day = datetime.date(year, month, last_day_of_month)

    return first_day, last_day


def get_quarter_range(date_obj: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """
    Возвращает первый и последний день квартала.

    Args:
        date_obj: Дата, для которой нужно определить диапазон квартала

    Returns:
        Tuple[datetime.date, datetime.date]: Кортеж из первого и последнего дня квартала
    """
    year = date_obj.year
    month = date_obj.month

    quarter = (month - 1) // 3 + 1

    first_month = (quarter - 1) * 3 + 1

    first_day = datetime.date(year, first_month, 1)

    last_month = first_month + 2

    _, last_day_of_month = calendar.monthrange(year, last_month)
    last_day = datetime.date(year, last_month, last_day_of_month)

    return first_day, last_day


def get_week_range(date_obj: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """
    Возвращает первый (понедельник) и последний (воскресенье) день недели.

    Args:
        date_obj: Дата, для которой нужно определить диапазон недели

    Returns:
        Tuple[datetime.date, datetime.date]: Кортеж из первого и последнего дня недели
    """

    weekday = date_obj.weekday()
    monday = date_obj - datetime.timedelta(days=weekday)
    sunday = monday + datetime.timedelta(days=6)

    return monday, sunday


def format_date_for_display(date_obj: datetime.date, format_type: str = "full") -> str:
    """
    Форматирует дату для отображения в разных форматах.

    Args:
        date_obj: Дата для форматирования
        format_type: Тип формата ('full', 'short', 'day_month', 'month_year')

    Returns:
        str: Отформатированная дата
    """

    month_names = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }

    month_names_nominative = {
        1: "январь",
        2: "февраль",
        3: "март",
        4: "апрель",
        5: "май",
        6: "июнь",
        7: "июль",
        8: "август",
        9: "сентябрь",
        10: "октябрь",
        11: "ноябрь",
        12: "декабрь",
    }

    if format_type == "full":

        return f"{date_obj .day } {month_names [date_obj .month ]} {date_obj .year }"
    elif format_type == "short":

        return date_obj.strftime("%d.%m.%Y")
    elif format_type == "day_month":

        return f"{date_obj .day } {month_names [date_obj .month ]}"
    elif format_type == "month_year":

        return f"{month_names_nominative [date_obj .month ]} {date_obj .year }"
    else:
        raise ValueError(f"Unknown format type: {format_type }")


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
    formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]

    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(
        f"Неверный формат даты: {date_str }. Поддерживаемые форматы: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD"
    )
