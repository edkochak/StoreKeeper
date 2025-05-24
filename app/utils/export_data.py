"""
Демонстрация работы с парсером Excel данных
"""

import asyncio
import pandas as pd
from app.services.excel_parser import ExcelDataParser
from app.core.database import get_session
from app.services.data_import_service import DataImportService


async def demo_database_import():
    """Демонстрация импорта данных в базу (требует настроенную БД)"""
    print("\n" + "=" * 50)
    print("=== Демонстрация импорта в базу данных ===")
    print("(Требует настроенную базу данных)\n")

    try:
        async with get_session() as session:
            import_service = DataImportService(session)

            imported, errors = await import_service.import_from_excel(
                file_path="resources/Book1.xlsx",
                store_id=1,
                shop_row=1,
                overwrite_existing=False,
            )
            print(f"✅ Импортировано записей: {len (imported )}")
            if errors:
                print(f"⚠️ Ошибки при валидации ({len (errors )}):")
                for err in errors:
                    print(f"  - {err }")

        async with get_session() as session:
            import_service = DataImportService(session)

            imported, errors = await import_service.import_from_excel(
                file_path="resources/Book1.xlsx",
                store_id=2,
                shop_row=159,
                overwrite_existing=False,
            )
            print(f"✅ Импортировано записей: {len (imported )}")
            if errors:
                print(f"⚠️ Ошибки при валидации ({len (errors )}):")
                for err in errors:
                    print(f"  - {err }")

    except Exception as e:
        print(f"ℹ️  База данных недоступна: {e }")


if __name__ == "__main__":

    asyncio.run(demo_database_import())
