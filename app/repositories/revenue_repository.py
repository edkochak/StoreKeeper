from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete
from app.models.revenue import Revenue


class RevenueRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, amount: float, store_id: int, manager_id: int, date_: date
    ) -> Revenue:

        query = select(Revenue).filter_by(store_id=store_id, date=date_)
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            existing.amount = amount
            existing.manager_id = manager_id
            await self.session.commit()
            await self.session.refresh(existing)

            await self.session.execute(
                delete(Revenue).where(
                    Revenue.store_id == store_id,
                    Revenue.date == date_,
                    Revenue.id != existing.id,
                )
            )
            await self.session.commit()
            return existing

        revenue = Revenue(
            amount=amount, store_id=store_id, manager_id=manager_id, date=date_
        )
        self.session.add(revenue)
        await self.session.commit()
        await self.session.refresh(revenue)

        await self.session.execute(
            delete(Revenue).where(
                Revenue.store_id == store_id,
                Revenue.date == date_,
                Revenue.id != revenue.id,
            )
        )
        await self.session.commit()
        return revenue

    async def get_by_store(self, store_id: int) -> List[Revenue]:
        result = await self.session.execute(
            select(Revenue)
            .options(
                selectinload(Revenue.manager),
                selectinload(Revenue.store),
            )
            .filter_by(store_id=store_id)
        )
        return result.scalars().all()

    async def get_all(self) -> List[Revenue]:
        result = await self.session.execute(
            select(Revenue).options(
                selectinload(Revenue.manager),
                selectinload(Revenue.store),
            )
        )
        return result.scalars().all()

    async def get_sum_for_period(
        self, store_id: int, start_date: date, end_date: date
    ) -> float:
        """Получить сумму выручки за указанный период для магазина"""
        query = select(func.sum(Revenue.amount)).filter(
            Revenue.store_id == store_id,
            Revenue.date >= start_date,
            Revenue.date <= end_date,
        )

        result = await self.session.execute(query)
        total = result.scalar()
        return total or 0.0
