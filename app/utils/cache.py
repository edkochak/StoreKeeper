import json
import logging
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union
from app.core.config import REDIS_DSN
import redis.asyncio as redis

# Настройка логгера
logger = logging.getLogger(__name__)

# Инициализация соединения с Redis
try:
    redis_client = redis.from_url(REDIS_DSN, decode_responses=True)
    logger.info("Redis connection initialized")
except Exception as e:
    logger.error(f"Failed to initialize Redis connection: {e}")

    # Создаем заглушку для тестов, которая логирует операции
    class RedisMock:
        async def get(self, key: str) -> Optional[str]:
            logger.warning(f"Mock Redis GET operation: {key}")
            return None

        async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
            logger.warning(f"Mock Redis SET operation: {key}, TTL: {ex}")
            return True

        async def delete(self, *keys: str) -> int:
            logger.warning(f"Mock Redis DELETE operation: {keys}")
            return len(keys)

        async def keys(self, pattern: str) -> List[str]:
            logger.warning(f"Mock Redis KEYS operation: {pattern}")
            return []

    redis_client = RedisMock()
    logger.warning("Using Redis mock for testing")


def get_cache_key(*args: Any) -> str:
    """
    Генерирует ключ для кэша на основе переданных аргументов.

    Args:
        *args: Произвольные аргументы для формирования ключа

    Returns:
        str: Сгенерированный ключ кэша
    """
    if not args:
        raise ValueError("Cache key cannot be empty")

    parts = []
    for arg in args:
        if isinstance(arg, dict):
            # Для словарей включаем ключи-значения в строку ключа
            dict_parts = []
            for k, v in sorted(arg.items()):
                dict_parts.append(f"{k}:{v}")
            parts.append("-".join(dict_parts))
        elif isinstance(arg, (list, tuple, set)):
            # Для списков и других коллекций преобразуем элементы
            parts.append("-".join(str(item) for item in arg))
        else:
            parts.append(str(arg))

    return ":".join(parts)


async def get_cached_data(key: str) -> Optional[Any]:
    """
    Получает данные из кэша по ключу.

    Args:
        key: Ключ для получения данных

    Returns:
        Optional[Any]: Данные из кэша или None, если кэш не найден
    """
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Error getting data from cache: {e}")
        return None


async def set_cached_data(key: str, data: Any, ttl: int = 3600) -> bool:
    """
    Сохраняет данные в кэш.

    Args:
        key: Ключ для сохранения данных
        data: Данные для сохранения (будут сериализованы в JSON)
        ttl: Время жизни кэша в секундах (по умолчанию 1 час)

    Returns:
        bool: True если данные успешно сохранены, False в случае ошибки
    """
    try:
        serialized_data = json.dumps(data)
        await redis_client.set(key, serialized_data, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error setting data to cache: {e}")
        return False


async def invalidate_cache(
    key: Optional[str] = None, pattern: Optional[str] = None
) -> int:
    """
    Инвалидирует кэш по ключу или паттерну.

    Args:
        key: Конкретный ключ для удаления
        pattern: Паттерн для поиска ключей (например, "store:*:stats")

    Returns:
        int: Количество удаленных ключей
    """
    try:
        if key:
            return await redis_client.delete(key)
        elif pattern:
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return 0
