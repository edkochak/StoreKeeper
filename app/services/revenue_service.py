from datetime import date
from typing import Tuple, Dict, Optional
import io
import pandas as pd
import matplotlib.pyplot as plt
import logging
import calendar

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.revenue_repository import RevenueRepository
from app.repositories.store_repository import StoreRepository
from app.core.config import DEFAULT_PLAN

logger = logging.getLogger(__name__)


class RevenueService:
    def __init__(self, session: AsyncSession):
        self.repo = RevenueRepository(session)

    async def create_revenue(
        self, amount: float, store_id: int, manager_id: int, date_: date
    ):
        # Проверяем существующую запись выручки для этого менеджера, магазина и даты
        existing = await self.repo.get_by_unique_key(store_id, manager_id, date_)

        # Если запись существует - обновляем её
        if existing:
            logger.info(
                "Перезапись выручки: магазин=%d, менеджер=%d, дата=%s, сумма=%.2f -> %.2f",
                store_id,
                manager_id,
                date_,
                existing.amount,
                amount,
            )
            return await self.repo.update_amount(existing, amount)

        # Если записи нет - создаём новую
        logger.info(
            "Создание новой выручки: магазин=%d, менеджер=%d, дата=%s, сумма=%.2f",
            store_id,
            manager_id,
            date_,
            amount,
        )
        return await self.repo.create(amount, store_id, manager_id, date_)

    async def export_report(self) -> Tuple[bytes, Dict[str, bytes]]:
        # Получаем все данные выручки
        revenues = await self.repo.get_all()
        # Преобразуем в DataFrame
        data = [
            (
                r.store.name,
                r.manager.first_name + " " + r.manager.last_name,
                r.date,
                r.amount,
            )
            for r in revenues
        ]
        df = pd.DataFrame(data, columns=["store", "manager", "date", "amount"])
        # Сводная таблица: суммы по магазинам
        summary = df.groupby("store")["amount"].sum().reset_index()
        logger.info("Генерация Excel отчета: %d записей выручки", len(df))
        # Генерация Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Details", index=False)
            summary.to_excel(writer, sheet_name="Summary", index=False)
        excel_bytes = output.getvalue()
        # Генерация графиков для каждого магазина с индивидуальными планами
        images = {}
        # репозиторий для доступа к планам магазинов
        store_repo = StoreRepository(self.repo.session)
        for _, row in summary.iterrows():
            store_name = row["store"]
            total = row["amount"]
            # получаем объект магазина для плана
            store_obj = await store_repo.get_by_name(store_name)
            plan = store_obj.plan if store_obj else DEFAULT_PLAN
            logger.info(
                "Построение графика для %s: план=%.2f, факт=%.2f",
                store_name,
                plan,
                total,
            )
            fig, ax = plt.subplots()
            ax.bar(["Plan", "Actual"], [plan, total], color=["gray", "green"])
            ax.set_title(f"Revenue for {store_name}")
            ax.set_ylabel("Amount")
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            plt.close(fig)
            images[store_name] = buf.getvalue()
        return excel_bytes, images

    async def get_month_total(self, store_id: int) -> float:
        """Получить общую выручку за текущий месяц"""
        today = date.today()
        # Первый день текущего месяца
        first_day = date(today.year, today.month, 1)
        # Последний день текущего месяца
        _, last_day_num = calendar.monthrange(today.year, today.month)
        last_day = date(today.year, today.month, last_day_num)

        return await self.repo.get_sum_for_period(store_id, first_day, last_day)

    async def get_matryoshka_data(self) -> list:
        """Подготовка данных для отчетов в виде матрешек"""
        # Получаем все данные выручки
        revenues = await self.repo.get_all()

        # Группируем данные по магазинам
        stores_data = {}
        for r in revenues:
            store_name = r.store.name
            if store_name not in stores_data:
                stores_data[store_name] = {
                    "store": r.store,
                    "total": 0,
                    "latest_date": date(1, 1, 1),  # Начальная дата для сравнения
                    "latest_amount": 0,
                }

            # Суммируем выручку
            stores_data[store_name]["total"] += r.amount

            # Отслеживаем последнюю дату и сумму
            if r.date > stores_data[store_name]["latest_date"]:
                stores_data[store_name]["latest_date"] = r.date
                stores_data[store_name]["latest_amount"] = r.amount

        # Преобразуем в формат для матрешек
        result = []
        for store_name, data in stores_data.items():
            store = data["store"]
            total_amount = data["total"]
            plan = store.plan if store.plan > 0 else DEFAULT_PLAN
            fill_percent = min(int((total_amount / plan) * 100), 100) if plan > 0 else 0

            # Определение цвета в зависимости от процента выполнения плана
            fill_color = self._get_color_by_progress(fill_percent)

            # Форматирование сумм для отображения
            formatted_total = f"{total_amount:,.0f}".replace(",", " ")
            formatted_plan = f"{plan:,.0f}".replace(",", " ")
            formatted_daily = f"{data['latest_amount']:,.0f}".replace(",", " ")

            # Форматирование даты
            formatted_date = data["latest_date"].strftime("%d.%m.%y")

            result.append(
                {
                    "title": store_name,
                    "fill_percent": fill_percent,
                    "daily_amount": formatted_daily,
                    "day": formatted_date,
                    "total_amount": formatted_total,
                    "plan_amount": formatted_plan,
                    "fill_color": fill_color,
                }
            )

        return result

    def _get_color_by_progress(self, percent: int) -> tuple:
        """Определяет цвет в зависимости от прогресса выполнения плана"""
        # Красный -> Желтый -> Зеленый
        if percent < 30:
            return (178, 34, 34, 200)  # Красный
        elif percent < 70:
            return (218, 165, 32, 200)  # Золотистый
        else:
            return (34, 139, 34, 200)  # Зеленый
