#!/usr/bin/env python3
"""
Демонстрация работы с парсером Excel данных
"""

import asyncio
import pandas as pd
from app.services.excel_parser import ExcelDataParser
from app.core.database import get_session
from app.services.data_import_service import DataImportService



def demo_multiple_shops():
    """Демонстрация парсинга нескольких магазинов"""
    print("\n" + "="*50)
    print("=== Парсинг нескольких магазинов ===\n")
    
    parser = ExcelDataParser()
    
    try:
        # Парсим данные для строк 1, 2, 3 (если существуют)
        shop_rows = [1, 159]
        results = parser.parse_multiple_shops("resources/Book1.xlsx", shop_rows)
        
        for row_num, shop_data in results.items():
            print(f"Магазин (строка {row_num}):")
            if shop_data:
                valid_data, errors = parser.validate_data(shop_data)
                print(f"  📦 Записей: {len(shop_data)}")
                print(f"  ✅ Валидных: {len(valid_data)}")
                if errors:
                    print(f"  ❌ Ошибок: {len(errors)}")
                
                if valid_data:
                    total = sum(record['revenue'] for record in valid_data)
                    print(f"  💰 Общая выручка: {total:,.2f} руб.")
            else:
                print("  📭 Нет данных")
            print()
            
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")


async def demo_database_import():
    """Демонстрация импорта данных в базу (требует настроенную БД)"""
    print("\n" + "="*50)
    print("=== Демонстрация импорта в базу данных ===")
    print("(Требует настроенную базу данных)\n")
    
    try:
        async with get_session() as session:
            import_service = DataImportService(session)
            # Пример импорта для магазина с ID 1 и строки 1
            imported, errors = await import_service.import_from_excel(
                file_path='resources/Book1.xlsx',
                store_id=1,
                shop_row=1,
                overwrite_existing=False
            )
            print(f"✅ Импортировано записей: {len(imported)}")
            if errors:
                print(f"⚠️ Ошибки при валидации ({len(errors)}):")
                for err in errors:
                    print(f"  - {err}")
     
    except Exception as e:
        print(f"ℹ️  База данных недоступна: {e}")


if __name__ == "__main__":
    # Демонстрация импорта в базу данных
    asyncio.run(demo_database_import())