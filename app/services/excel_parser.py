import pandas as pd
import datetime
from typing import List, Dict, Tuple


class ExcelDataParser:
    """
    Парсер данных выручки из Excel файлов.
    """
    def parse_revenue_data(self, file_path: str, shop_row: int) -> List[Dict]:
        """
        Читает данные продаж из указанного Excel файла для заданного номера строки магазина.
        """
        try:
            df = pd.read_excel(file_path, header=0)
        except Exception as e:
            raise RuntimeError(f"Не удалось прочитать Excel-файл: {e}")

        records: List[Dict] = []
        cols = df.columns.tolist()
        for idx, col in enumerate(cols):
            # пытаемся разобрать заголовок как дату
            try:
                date_val = pd.to_datetime(col, dayfirst=True).date()
            except Exception:
                continue
            # следующий столбец содержит выручку
            if idx + 1 >= len(cols):
                continue
            rev_col = cols[idx + 1]
            raw_rev = df.iloc[shop_row, idx + 1]
            # Заменяем NaN на 0
            if pd.isna(raw_rev):
                rev_val = 0.0
            else:
                try:
                    rev_val = float(raw_rev)
                except Exception:
                    rev_val = 0.0
            records.append({
                'date': date_val,
                'revenue': rev_val,
            })
        return records

    def validate_data(self, data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Проверяет корректность дат и выручки в списке записей.
        """
        valid: List[Dict] = []
        errors: List[str] = []
        for idx, item in enumerate(data, 1):
            if not isinstance(item.get('date'), datetime.date):
                errors.append(f"Запись {idx}: неверная дата {item.get('date')}")
                continue
            if not isinstance(item.get('revenue'), (int, float)):
                errors.append(f"Запись {idx}: неверная выручка {item.get('revenue')}")
                continue
            valid.append(item)
        return valid, errors

    def parse_multiple_shops(self, file_path: str, shop_rows: List[int]) -> Dict[int, List[Dict]]:
        """
        Возвращает данные по нескольким магазинам.
        """
        results: Dict[int, List[Dict]] = {}
        for row in shop_rows:
            try:
                data = self.parse_revenue_data(file_path, row)
                results[row] = data
            except Exception:
                results[row] = []
        return results
