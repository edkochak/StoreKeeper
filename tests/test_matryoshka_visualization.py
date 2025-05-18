import pytest
import io
from PIL import Image
from app.utils.matryoshka import create_matryoshka_collection
from app.services.revenue_service import RevenueService


def test_matryoshka_color():
    """Тест цвета матрешки"""

    img = Image.new("RGBA", (300, 500), (255, 255, 255, 0))
    img_bytes = io.BytesIO()
    img.save(img_bytes, "PNG")
    img_bytes.seek(0)

    low_progress = {
        "title": "Low Store",
        "fill_percent": 20,
        "daily_amount": "1000",
        "day": "01.05.23",
        "total_amount": "5000",
        "plan_amount": "25000",
    }

    medium_progress = {
        "title": "Medium Store",
        "fill_percent": 50,
        "daily_amount": "1000",
        "day": "01.05.23",
        "total_amount": "12500",
        "plan_amount": "25000",
    }

    high_progress = {
        "title": "High Store",
        "fill_percent": 90,
        "daily_amount": "1000",
        "day": "01.05.23",
        "total_amount": "22500",
        "plan_amount": "25000",
    }

    service = RevenueService(None)

    low_color = service._get_color_by_progress(20)
    medium_color = service._get_color_by_progress(50)
    high_color = service._get_color_by_progress(90)

    assert low_color == medium_color == high_color

    assert low_color[0] == 70
    assert low_color[1] == 130
    assert low_color[2] == 180

    shops_data = [low_progress, medium_progress, high_progress]

    template_path = str(img_bytes.getvalue())

    try:

        service._get_color_by_progress(20)
    except Exception as e:
        assert False, f"Метод _get_color_by_progress вызвал исключение: {e }"
