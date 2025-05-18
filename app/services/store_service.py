from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.repositories.store_repository import StoreRepository
from app.models.store import Store
import logging

logger = logging.getLogger(__name__)


class StoreService:
    def __init__(self, session: AsyncSession):
        self.repo = StoreRepository(session)

    async def list_stores(self) -> List[Store]:
        return await self.repo.get_all()

    async def get_or_create(self, name: str) -> Store:
        store = await self.repo.get_by_name(name)
        if not store:
            store = await self.repo.create(name)
        return store

    async def set_plan(self, store: Store, plan: float) -> Store:
        logger.info("Установка плана для магазина %s: %s", store.name, plan)
        return await self.repo.update_plan(store, plan)

    async def get_by_id(self, store_id: int) -> Store:
        """Получить магазин по ID"""
        return await self.repo.get_by_id(store_id)

    async def get_by_name(self, name: str) -> Optional[Store]:
        """Получить магазин по имени"""
        return await self.repo.get_by_name(name)

    async def update_name(self, store: Store, new_name: str) -> Store:
        """Обновить название магазина"""
        logger.info("Изменение названия магазина %s на %s", store.name, new_name)
        return await self.repo.update_name(store, new_name)

    async def delete_store(self, store: Store) -> None:
        await self.repo.delete_store(store)
