import logging
from typing import Optional, List
from datetime import date
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSession
from app.models.monthly_plan import MonthlyPlan

logger = logging.getLogger(__name__)


class MonthlyPlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_plan(
        self, store_id: int, month_year: date, plan_amount: float
    ) -> Optional[MonthlyPlan]:
        """Создает план на месяц для магазина"""
        try:
            plan = MonthlyPlan(
                store_id=store_id, month_year=month_year, plan_amount=plan_amount
            )
            self.session.add(plan)
            await self.session.commit()
            await self.session.refresh(plan)
            logger.info(
                f"Создан план для магазина {store_id } на {month_year }: {plan_amount }"
            )
            return plan
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Ошибка создания плана: {e }")
            return None
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Неожиданная ошибка при создании плана: {e }")
            return None

    async def update_plan(
        self, store_id: int, month_year: date, plan_amount: float
    ) -> Optional[MonthlyPlan]:
        """Обновляет план на месяц для магазина"""
        try:
            result = await self.session.execute(
                select(MonthlyPlan).where(
                    MonthlyPlan.store_id == store_id,
                    MonthlyPlan.month_year == month_year,
                )
            )
            plan = result.scalar_one_or_none()

            if plan:
                plan.plan_amount = plan_amount
                await self.session.commit()
                await self.session.refresh(plan)
                logger.info(
                    f"Обновлен план для магазина {store_id } на {month_year }: {plan_amount }"
                )
                return plan
            else:

                return await self.create_plan(store_id, month_year, plan_amount)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка обновления плана: {e }")
            return None

    async def get_plan(self, store_id: int, month_year: date) -> Optional[MonthlyPlan]:
        """Получает план на месяц для магазина"""
        try:
            result = await self.session.execute(
                select(MonthlyPlan).where(
                    MonthlyPlan.store_id == store_id,
                    MonthlyPlan.month_year == month_year,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения плана: {e }")
            return None

    async def get_store_plans(self, store_id: int) -> List[MonthlyPlan]:
        """Получает все планы для магазина"""
        try:
            result = await self.session.execute(
                select(MonthlyPlan)
                .where(MonthlyPlan.store_id == store_id)
                .order_by(MonthlyPlan.month_year)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения планов магазина: {e }")
            return []

    async def delete_plan(self, store_id: int, month_year: date) -> bool:
        """Удаляет план на месяц для магазина"""
        try:
            await self.session.execute(
                delete(MonthlyPlan).where(
                    MonthlyPlan.store_id == store_id,
                    MonthlyPlan.month_year == month_year,
                )
            )
            await self.session.commit()
            logger.info(f"Удален план для магазина {store_id } на {month_year }")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка удаления плана: {e }")
            return False
