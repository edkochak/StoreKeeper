import pytest
import pandas as pd
import io
from unittest.mock import patch, MagicMock
from app.services.revenue_service import RevenueService


@pytest.mark.asyncio
async def test_excel_report_structure(session):
    """Тест структуры Excel-отчета"""
    # Создаем сервис
    service = RevenueService(session)

    # Патчим метод get_revenue_for_report, чтобы он возвращал тестовые данные
    test_data = [
        {
            "store_name": "Магазин №1",
            "date": "2023-05-01",
            "amount": 1000.0,
            "plan": 5000.0,
        },
        {
            "store_name": "Магазин №1",
            "date": "2023-05-02",
            "amount": 1200.0,
            "plan": 5000.0,
        },
        {
            "store_name": "Магазин №2",
            "date": "2023-05-01",
            "amount": 800.0,
            "plan": 4000.0,
        },
        {
            "store_name": "Магазин №2",
            "date": "2023-05-02",
            "amount": 850.0,
            "plan": 4000.0,
        },
    ]

    with patch.object(
        RevenueService, "_get_revenue_for_report", return_value=test_data
    ):
        # Генерируем отчет
        excel_bytes, _ = await service.export_report()

        # Проверяем, что отчет сгенерирован
        assert excel_bytes is not None
        assert isinstance(excel_bytes, bytes)

        # Загружаем Excel-файл с помощью pandas
        excel_file = pd.ExcelFile(io.BytesIO(excel_bytes))

        # Проверяем наличие нужных листов
        assert "Выручка по дням" in excel_file.sheet_names
        assert "Сводка по магазинам" in excel_file.sheet_names

        # Проверяем содержимое листа "Выручка по дням"
        df_daily = pd.read_excel(excel_file, "Выручка по дням")
        assert "Дата" in df_daily.columns
        assert "Магазин" in df_daily.columns
        assert "Выручка" in df_daily.columns
        assert len(df_daily) == 4  # 4 записи

        # Проверяем содержимое листа "Сводка по магазинам"
        df_summary = pd.read_excel(excel_file, "Сводка по магазинам")
        assert "Магазин" in df_summary.columns
        assert "Общая выручка" in df_summary.columns
        assert "План" in df_summary.columns
        assert "% выполнения" in df_summary.columns
        assert len(df_summary) == 2  # 2 магазина


@pytest.mark.asyncio
async def test_matryoshka_data_preparation(session):
    """Тест подготовки данных для визуализации матрешек"""
    # Создаем сервис
    service = RevenueService(session)

    # Патчим метод _get_revenue_stats, чтобы он возвращал тестовые данные
    test_stats = [
        {
            "store_id": 1,
            "store_name": "Магазин №1",
            "total": 2200.0,
            "plan": 5000.0,
            "last_revenue": {"amount": 1200.0, "date": "2023-05-02"},
        },
        {
            "store_id": 2,
            "store_name": "Магазин №2",
            "total": 1650.0,
            "plan": 4000.0,
            "last_revenue": {"amount": 850.0, "date": "2023-05-02"},
        },
    ]

    with patch.object(RevenueService, "_get_revenue_stats", return_value=test_stats):
        # Получаем данные для матрешек
        matryoshka_data = await service.get_matryoshka_data()

        # Проверяем структуру данных
        assert len(matryoshka_data) == 2

        # Проверяем первый магазин
        store1 = next(item for item in matryoshka_data if item["title"] == "Магазин №1")
        assert store1["fill_percent"] == 44  # 2200 / 5000 * 100 = 44%
        assert store1["daily_amount"] == "1 200"
        assert store1["day"] == "02.05.23"
        assert store1["total_amount"] == "2 200"
        assert store1["plan_amount"] == "5 000"

        # Проверяем второй магазин
        store2 = next(item for item in matryoshka_data if item["title"] == "Магазин №2")
        assert store2["fill_percent"] == 41  # 1650 / 4000 * 100 = 41.25% ≈ 41%
        assert store2["daily_amount"] == "850"
        assert store2["day"] == "02.05.23"
        assert store2["total_amount"] == "1 650"
        assert store2["plan_amount"] == "4 000"
