import pytest
from datetime import date, datetime, timedelta
from app.utils.date_utils import (
    get_month_range,
    get_quarter_range,
    get_week_range,
    format_date_for_display,
)


def test_month_range_calculation():
    """Тест расчета диапазона месяца"""

    start, end = get_month_range(date(2023, 5, 15))
    assert start == date(2023, 5, 1)
    assert end == date(2023, 5, 31)

    start, end = get_month_range(date(2024, 2, 10))
    assert start == date(2024, 2, 1)
    assert end == date(2024, 2, 29)

    start, end = get_month_range(date(2023, 2, 10))
    assert start == date(2023, 2, 1)
    assert end == date(2023, 2, 28)


def test_quarter_range_calculation():
    """Тест расчета диапазона квартала"""

    start, end = get_quarter_range(date(2023, 2, 15))
    assert start == date(2023, 1, 1)
    assert end == date(2023, 3, 31)

    start, end = get_quarter_range(date(2023, 5, 10))
    assert start == date(2023, 4, 1)
    assert end == date(2023, 6, 30)

    start, end = get_quarter_range(date(2023, 8, 22))
    assert start == date(2023, 7, 1)
    assert end == date(2023, 9, 30)

    start, end = get_quarter_range(date(2023, 12, 25))
    assert start == date(2023, 10, 1)
    assert end == date(2023, 12, 31)


def test_week_range_calculation():
    """Тест расчета диапазона недели"""

    date_obj = date(2023, 5, 15)
    start, end = get_week_range(date_obj)
    assert start == date(2023, 5, 15)
    assert end == date(2023, 5, 21)

    date_obj = date(2023, 5, 20)
    start, end = get_week_range(date_obj)
    assert start == date(2023, 5, 15)
    assert end == date(2023, 5, 21)


def test_date_formatting():
    """Тест форматирования даты для отображения"""

    date_obj = date(2023, 5, 15)
    assert format_date_for_display(date_obj, "full") == "15 мая 2023"

    assert format_date_for_display(date_obj, "short") == "15.05.2023"

    assert format_date_for_display(date_obj, "day_month") == "15 мая"

    assert format_date_for_display(date_obj, "month_year") == "май 2023"
