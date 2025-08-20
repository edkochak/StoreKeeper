from app.utils.validators import (
    is_valid_email,
    is_valid_phone,
    sanitize_input,
    is_valid_store_name,
)


def test_is_valid_email():
    assert is_valid_email("user@example.com")
    assert not is_valid_email("user@@example.com")
    assert not is_valid_email("user@invalid")


def test_is_valid_phone():
    assert is_valid_phone("+79991234567")
    assert is_valid_phone("+12345678901")
    assert not is_valid_phone("12345")
    assert not is_valid_phone("+7-abc-123")


def test_sanitize_input_and_store_name():
    dirty = "<script>alert('x');</script>"
    clean = sanitize_input(dirty)
    assert "<" not in clean and ">" not in clean and "'" not in clean and ";" not in clean

    assert not is_valid_store_name("Store; DROP TABLE users;")
    assert not is_valid_store_name("UNION SELECT * FROM users")
    assert is_valid_store_name("Normal Store")
