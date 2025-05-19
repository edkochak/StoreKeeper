import pytest
import json
from unittest.mock import patch, AsyncMock
from app.utils.cache import (
    get_cached_data,
    set_cached_data,
    invalidate_cache,
    get_cache_key,
)


@pytest.mark.asyncio
async def test_cache_operations():
    """Тест базовых операций с кэшем"""

    redis_mock = AsyncMock()
    redis_mock.get.return_value = None

    test_key = "test_key"
    test_data = {"name": "Test Data", "value": 123}

    with patch("app.utils.cache.redis_client", redis_mock):
        cached_data = await get_cached_data(test_key)
        assert cached_data is None
        redis_mock.get.assert_called_once_with(test_key)

    redis_mock.reset_mock()
    redis_mock.set.return_value = True
    with patch("app.utils.cache.redis_client", redis_mock):
        await set_cached_data(test_key, test_data, ttl=3600)
        redis_mock.set.assert_called_once()

        json_data = json.dumps(test_data)
        redis_mock.set.assert_called_with(test_key, json_data, ex=3600)

    redis_mock.reset_mock()
    redis_mock.get.return_value = json.dumps(test_data)
    with patch("app.utils.cache.redis_client", redis_mock):
        cached_data = await get_cached_data(test_key)
        assert cached_data == test_data
        redis_mock.get.assert_called_once_with(test_key)

    redis_mock.reset_mock()
    with patch("app.utils.cache.redis_client", redis_mock):
        await invalidate_cache(test_key)
        redis_mock.delete.assert_called_once_with(test_key)


@pytest.mark.asyncio
async def test_cache_with_pattern_invalidation():
    """Тест инвалидации кэша по паттерну"""

    redis_mock = AsyncMock()
    redis_mock.keys.return_value = []

    pattern = "store:1:*"

    with patch("app.utils.cache.redis_client", redis_mock):
        await invalidate_cache(pattern=pattern)
        redis_mock.keys.assert_called_once_with(pattern)
        assert redis_mock.delete.call_count == 1


def test_cache_key_generation():
    """Тест генерации ключей кэша"""

    key = get_cache_key("store", 1)
    assert key == "store:1"

    key = get_cache_key("revenue", "store", 1, "date", "2023-05-15")
    assert key == "revenue:store:1:date:2023-05-15"

    key = get_cache_key("complex", {"id": 1, "name": "test"}, ["a", "b", "c"])
    assert isinstance(key, str)
    assert "complex" in key
    assert "id" in key and "name" in key
    assert "a" in key and "b" in key and "c" in key
