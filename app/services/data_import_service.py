from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import MultipleResultsFound


class DataImportService:
    """
    Сервис для импорта данных из Excel в базу данных.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_from_excel(
        self,
        file_path: str,
        store_id: int,
        shop_row: int,
        overwrite_existing: bool = False,
    ):
        """
        Импортирует данные выручки из Excel в базу данных.

        Args:
            file_path: путь к Excel-файлу
            store_id: ID магазина для привязки данных
            shop_row: номер строки с данными магазина в Excel
            overwrite_existing: перезаписывать ли существующие записи

        Returns:
            Tuple[List[Revenue], List[str]]: список импортированных записей и список ошибок валидации
        """

        from app.repositories.store_repository import StoreRepository
        from app.repositories.revenue_repository import RevenueRepository
        from app.services.excel_parser import ExcelDataParser

        store_repo = StoreRepository(self.session)
        revenue_repo = RevenueRepository(self.session)
        parser = ExcelDataParser()

        store = await store_repo.get_by_id(store_id)
        if not store:
            raise ValueError(f"Магазин с ID {store_id } не найден")

        parsed = parser.parse_revenue_data(file_path, shop_row)
        valid_data, errors = parser.validate_data(parsed)

        imported = []

        if not store.managers:
            raise ValueError(
                f"Для магазина {store .name } не назначен ни один менеджер"
            )
        manager_id = store.managers[0].id

        for record in valid_data:
            try:
                revenue = await revenue_repo.create(
                    amount=record["revenue"],
                    store_id=store_id,
                    manager_id=manager_id,
                    date_=record["date"],
                )
                imported.append(revenue)
            except MultipleResultsFound:
                errors.append(f"Дублирование записей для даты {record ['date']}")
            except Exception as e:
                errors.append(f"Ошибка импорта записи на {record ['date']}: {e }")

        return imported, errors
