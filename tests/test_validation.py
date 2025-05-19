import pytest
import datetime
from app.utils.validators import (
    validate_revenue_amount,
    validate_date_format,
    is_valid_store_name,
)


def test_revenue_amount_validation():
    """Тест валидации суммы выручки"""

    assert validate_revenue_amount("100") == 100.0
    assert validate_revenue_amount("100.50") == 100.5
    assert validate_revenue_amount("100,50") == 100.5
    assert validate_revenue_amount("1000000") == 1000000.0

    assert validate_revenue_amount("-100") == -100.0
    assert validate_revenue_amount("-99.99") == -99.99
    assert validate_revenue_amount("-0.5") == -0.5

    with pytest.raises(ValueError):
        validate_revenue_amount("сто рублей")
    with pytest.raises(ValueError):
        validate_revenue_amount("")
    with pytest.raises(ValueError):
        validate_revenue_amount("100.50.25")


def test_date_format_validation():
    """Тест валидации формата даты"""

    assert validate_date_format("01.05.2023") == datetime.date(2023, 5, 1)
    assert validate_date_format("01/05/2023") == datetime.date(2023, 5, 1)
    assert validate_date_format("2023-05-01") == datetime.date(2023, 5, 1)

    with pytest.raises(ValueError):
        validate_date_format("01-05-23")
    with pytest.raises(ValueError):
        validate_date_format("32.05.2023")
    with pytest.raises(ValueError):
        validate_date_format("2023.05.01")
    with pytest.raises(ValueError):
        validate_date_format("вчера")


def test_store_name_validation():
    """Тест валидации названия магазина"""

    assert is_valid_store_name("Магазин №1")
    assert is_valid_store_name("ГУМ")
    assert is_valid_store_name("Торговый центр 'Галерея'")
    assert is_valid_store_name("Магазин на ул. Ленина, 10")

    assert not is_valid_store_name("")
    assert not is_valid_store_name("М" * 101)
    assert not is_valid_store_name("Магазин;DROP TABLE stores;")
