from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.store import Store
from app.models.user import User


class StoreRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Store]:

        result = await self.session.execute(
            select(Store).options(selectinload(Store.managers).selectinload(User.store))
        )
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[Store]:
        result = await self.session.execute(
            select(Store)
            .options(
                selectinload(Store.managers),
                selectinload(Store.revenues),
            )
            .filter_by(name=name)
        )
        return result.scalars().first()

    async def get_by_id(self, store_id: int) -> Optional[Store]:
        result = await self.session.execute(
            select(Store)
            .options(
                selectinload(Store.managers),
                selectinload(Store.revenues),
            )
            .filter_by(id=store_id)
        )
        return result.scalars().first()

    async def create(self, name: str) -> Store:
        store = Store(name=name)
        self.session.add(store)
        await self.session.commit()
        await self.session.refresh(store)
        return store

    async def update_plan(self, store: Store, plan: float) -> Store:
        store.plan = plan
        self.session.add(store)
        await self.session.commit()
        await self.session.refresh(store)
        return store

    async def update_name(self, store: Store, new_name: str) -> Store:
        """Обновить название магазина"""
        store.name = new_name
        self.session.add(store)
        await self.session.commit()
        await self.session.refresh(store)
        return store

    async def delete_store(self, store: Store) -> None:
        await self.session.delete(store)
        await self.session.commit()
