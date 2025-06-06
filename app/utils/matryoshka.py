from PIL import Image, ImageDraw, ImageOps, ImageFont
import numpy as np
import io
from typing import Tuple, Optional, List, Union, Dict, Any
from enum import Enum, auto
import os


class MatryoshkaFillBuilder:
    """
    Построитель (Builder) для создания изображений с заливкой матрешки.
    Реализует пошаговый процесс создания сложного изображения.
    """

    def __init__(self, image_path: str):
        """Инициализация с путем к изображению"""
        self.image_path = image_path
        self.base_image = None
        self.mask_array = None
        self.boundaries = None
        self.fill_layer = None
        self.result = None
        self.config = {
            "fill_percent": 40,
            "fill_color": (70, 130, 180, 200),
            "meniscus_width_factor": 0.30,
            "meniscus_max_height": 30,
            "meniscus_curve_factor": 6,
            "show_percent": True,
            "font_size": 50,
            "line_width": 3,
            "show_info": False,
            "title": "Название",
            "daily_amount": "0",
            "day": "01",
            "total_amount": "0",
            "plan_amount": "0",
            "info_text_color": (0, 0, 0, 255),
            "info_font_size": 36,
            "info_x_offset": 50,
            "percent_text_offset": 60,
        }

    def configure(self, **kwargs):
        """Настройка параметров заливки"""
        self.config.update(kwargs)
        return self

    def load_image(self):
        """Загрузка изображения и создание маски"""

        self.base_image = Image.open(self.image_path).convert("RGBA")
        width, height = self.base_image.size

        mask = self.base_image.convert("L")
        mask = ImageOps.invert(mask)
        mask = mask.point(lambda p: 255 if p > 50 else 0)
        arr = np.array(mask)

        if self.config.get("show_info", False):
            extra = self.config.get("info_x_offset", 50) + 500

            new_img = Image.new("RGBA", (width + extra, height), (0, 0, 0, 0))
            new_img.paste(self.base_image, (0, 0))
            self.base_image = new_img

            arr = np.pad(arr, ((0, 0), (0, extra)), constant_values=0)

        self.mask_array = arr
        return self

    def find_boundaries(self):
        """Определение границ объекта на изображении"""
        nonzero = np.argwhere(self.mask_array > 0)
        ymin = np.min(nonzero[:, 0])
        ymax = np.max(nonzero[:, 0])
        x_min = np.min(nonzero[:, 1])
        x_max = np.max(nonzero[:, 1])

        fill_height = int((ymax - ymin) * self.config["fill_percent"] / 100)
        y_fill_start = ymax - fill_height

        self.boundaries = {
            "ymin": ymin,
            "ymax": ymax,
            "x_min": x_min,
            "x_max": x_max,
            "y_fill_start": y_fill_start,
        }
        return self

    def create_fill_layer(self):
        """Создание слоя заливки с эффектом мениска"""

        self.fill_layer = Image.new("RGBA", self.base_image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(self.fill_layer)

        y_fill_start = self.boundaries["y_fill_start"]
        ymax = self.boundaries["ymax"]

        self._fill_with_meniscus(draw, y_fill_start, ymax)
        return self

    def _fill_with_meniscus(self, draw: ImageDraw.Draw, y_start: int, y_end: int):
        """Вспомогательный метод для создания заливки с мениском"""
        for y in range(y_start, y_end):

            row_indices = np.where(self.mask_array[y] > 0)[0]
            if len(row_indices) == 0:
                continue

            left_edge = np.min(row_indices)
            right_edge = np.max(row_indices)

            width = right_edge - left_edge

            meniscus_factor = 1 - (y - y_start) / max(y_end - y_start, 1)
            meniscus_height = (
                min(
                    width * self.config["meniscus_width_factor"],
                    self.config["meniscus_max_height"],
                )
                * meniscus_factor
            )

            points = self._generate_meniscus_points(
                left_edge, right_edge, y, width, meniscus_height
            )

            if len(points) > 2:
                draw.line(
                    points,
                    fill=self.config["fill_color"],
                    width=self.config["line_width"],
                )

                for i in range(min(3, len(points))):
                    draw.point(points[i], fill=self.config["fill_color"])
                    draw.point(points[-i - 1], fill=self.config["fill_color"])

    def _generate_meniscus_points(
        self, left: int, right: int, y: int, width: int, height: float
    ) -> List[Tuple[int, float]]:
        """Генерация точек для кривой мениска"""
        points = []
        curve_factor = self.config["meniscus_curve_factor"]

        for x in range(left, right + 1):

            rel_pos = (x - left) / max(width, 1)
            height_offset = height * curve_factor * rel_pos * (1 - rel_pos)
            points.append((x, y + height_offset))

        return points

    def add_percentage_text(self):
        """Добавление текста с процентом заполнения"""
        if not self.config["show_percent"]:
            return self

        if self.result is None:
            self.result = Image.alpha_composite(self.base_image, self.fill_layer)

        draw = ImageDraw.Draw(self.result)
        percent_text = f"{round (self .config ['fill_percent'])}%"

        try:
            font = ImageFont.truetype("Arial", self.config["font_size"])
        except IOError:
            font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), percent_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]

        left_offset = 20
        text_x = max(left_offset, self.boundaries["x_min"] - text_width - 30)

        offset = self.config.get("percent_text_offset", 10)
        text_y = max(self.boundaries["ymin"], self.boundaries["y_fill_start"] - offset)

        text_color = self.config["fill_color"][:3] + (255,)

        padding = 5
        text_bbox = draw.textbbox((text_x, text_y), percent_text, font=font)
        bg_bbox = (
            text_bbox[0] - padding,
            text_bbox[1] - padding,
            text_bbox[2] + padding,
            text_bbox[3] + padding,
        )
        draw.rectangle(bg_bbox, fill=(250, 250, 250, 180))

        draw.text((text_x, text_y), percent_text, font=font, fill=text_color)

        return self

    def add_info_text(self):
        """Добавление информационного текста справа от матрешки"""
        if not self.config["show_info"]:
            return self

        if self.result is None:
            self.result = Image.alpha_composite(self.base_image, self.fill_layer)

        draw = ImageDraw.Draw(self.result)

        fonts_to_try = [
            "Arial Unicode MS",
            "DejaVu Sans",
            "Segoe UI",
            "Roboto",
            "Arial",
            "Helvetica",
            "Liberation Sans",
            "FreeSans",
        ]

        title_font = normal_font = bold_font = None

        for font_name in fonts_to_try:
            try:

                title_font = ImageFont.truetype(
                    font_name, self.config["info_font_size"]
                )
                normal_font = ImageFont.truetype(
                    font_name, int(self.config["info_font_size"] * 0.8)
                )

                try:
                    bold_font = ImageFont.truetype(
                        f"{font_name } Bold", int(self.config["info_font_size"] * 0.9)
                    )
                except IOError:
                    try:
                        bold_font = ImageFont.truetype(
                            f"{font_name }-Bold",
                            int(self.config["info_font_size"] * 0.9),
                        )
                    except IOError:
                        bold_font = normal_font

                break
            except IOError:
                continue

        if title_font is None:
            title_font = normal_font = bold_font = ImageFont.load_default()

        text_x = self.boundaries["x_max"] + self.config["info_x_offset"]
        text_y = self.boundaries["ymin"] + 20

        text_color = self.config["info_text_color"]

        draw.text(
            (text_x, text_y), self.config["title"], font=title_font, fill=text_color
        )
        text_y += int(self.config["info_font_size"] * 1.5)

        amount_day_text = f"{self .config ['daily_amount']} - {self .config ['day']}"
        draw.text((text_x, text_y), amount_day_text, font=normal_font, fill=text_color)
        text_y += int(self.config["info_font_size"] * 1.8)

        draw.text((text_x, text_y), "ТОТАЛ", font=bold_font, fill=text_color)
        text_y += int(self.config["info_font_size"] * 1.2)

        total_text = f"{self .config ['total_amount']} / {self .config ['plan_amount']}"
        draw.text((text_x, text_y), total_text, font=normal_font, fill=text_color)

        return self

    def build(self, output_path: Optional[str] = None) -> io.BytesIO:
        """Финальная сборка и возврат результата"""
        if self.result is None:
            self.result = Image.alpha_composite(self.base_image, self.fill_layer)

        if self.config.get("show_info", False):
            w, h = self.result.size

            extra = self.config.get("info_x_offset", 50) + 150
            new_canvas = Image.new("RGBA", (w + extra, h), (250, 250, 250, 0))
            new_canvas.paste(self.result, (0, 0))
            self.result = new_canvas

        if output_path:
            self.result.save(output_path)

        img_buffer = io.BytesIO()
        self.result.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        return img_buffer

    def _get_color_by_progress(self, percent: int) -> tuple:
        """Определяет цвет матрешки - всегда одинаковый"""

        return (70, 130, 180, 200)


class LayoutStrategy(Enum):
    """Стратегии расположения матрешек в композиции"""

    VERTICAL = auto()
    HORIZONTAL = auto()
    GRID = auto()


class MatryoshkaData:
    """Контейнер данных для одной матрешки в композиции"""

    def __init__(
        self,
        fill_percent: int = 40,
        title: str = "Магазин",
        daily_amount: str = "0",
        day: str = "01",
        total_amount: str = "0",
        plan_amount: str = "0",
        fill_color: Tuple[int, int, int, int] = (70, 130, 180, 200),
    ):
        self.fill_percent = fill_percent
        self.title = title
        self.daily_amount = daily_amount
        self.day = day
        self.total_amount = total_amount
        self.plan_amount = plan_amount
        self.fill_color = fill_color


class MatryoshkaCompositionBuilder:
    """
    Строитель для создания композиций из нескольких матрешек.
    Применяет паттерны строитель и стратегия.
    """

    def __init__(self, template_image_path: str):
        """
        Инициализация построителя композиций

        Args:
            template_image_path: Путь к шаблону изображения матрешки
        """
        self.template_path = template_image_path
        self.matryoshkas: List[MatryoshkaData] = []
        self.layout_strategy = LayoutStrategy.VERTICAL
        self.max_per_image = 2
        self.padding = 0
        # Увеличиваем размер шрифта для информационного текста справа
        self.global_config = {
            "meniscus_width_factor": 0.30,
            "meniscus_max_height": 30,
            "meniscus_curve_factor": 6,
            "show_percent": True,
            "font_size": 100,
            "info_font_size": 80,
            "info_x_offset": 100,
        }

        with Image.open(template_image_path) as img:
            self.template_width, self.template_height = img.size

    def add_matryoshka(self, data: MatryoshkaData) -> "MatryoshkaCompositionBuilder":
        """Добавление матрешки в композицию"""
        self.matryoshkas.append(data)
        return self

    def set_layout(self, strategy: LayoutStrategy) -> "MatryoshkaCompositionBuilder":
        """Установка стратегии расположения"""
        self.layout_strategy = strategy
        return self

    def set_max_per_image(self, count: int) -> "MatryoshkaCompositionBuilder":
        """Установка максимального количества матрешек на одном изображении"""
        self.max_per_image = count
        return self

    def configure(self, **kwargs) -> "MatryoshkaCompositionBuilder":
        """Настройка глобальных параметров"""
        self.global_config.update(kwargs)
        return self

    def build(self, output_dir: str = "") -> List[io.BytesIO]:
        """
        Построение композиций из матрешек согласно выбранной стратегии

        Args:
            output_dir: Директория для сохранения результатов. Если указана,
                        изображения будут сохранены в файлы.

        Returns:
            Список буферов с изображениями
        """
        if not self.matryoshkas:
            return []

        groups = [
            self.matryoshkas[i : i + self.max_per_image]
            for i in range(0, len(self.matryoshkas), self.max_per_image)
        ]

        result_buffers = []

        for idx, group in enumerate(groups):

            if self.layout_strategy == LayoutStrategy.VERTICAL:
                buffer = self._create_vertical_layout(group)
            elif self.layout_strategy == LayoutStrategy.HORIZONTAL:
                buffer = self._create_horizontal_layout(group)
            else:
                buffer = self._create_grid_layout(group)

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                with open(
                    os.path.join(output_dir, f"matryoshka_group_{idx +1 }.png"), "wb"
                ) as f:
                    f.write(buffer.getvalue())

            result_buffers.append(buffer)

        return result_buffers

    def _create_vertical_layout(self, matryoshkas: List[MatryoshkaData]) -> io.BytesIO:
        """Вертикальное расположение матрешек с адаптивной шириной холста"""

        images = []
        for data in matryoshkas:
            params = {
                **self.global_config,
                "fill_percent": data.fill_percent,
                "fill_color": data.fill_color,
                "show_info": True,
                "title": data.title,
                "daily_amount": data.daily_amount,
                "day": data.day,
                "total_amount": data.total_amount,
                "plan_amount": data.plan_amount,
            }
            buf = (
                MatryoshkaFillBuilder(self.template_path)
                .configure(**params)
                .load_image()
                .find_boundaries()
                .create_fill_layer()
                .add_percentage_text()
                .add_info_text()
                .build()
            )
            images.append(Image.open(buf))

        widths = [img.width for img in images]
        heights = [img.height for img in images]
        comp_w = max(widths)
        comp_h = sum(heights) + self.padding * (len(images) - 1)

        comp = Image.new("RGBA", (comp_w, comp_h), (250, 250, 250, 255))

        y = 0
        for img in images:
            x = (comp_w - img.width) // 2
            comp.paste(img, (x, y), img)
            y += img.height + self.padding

        buf = io.BytesIO()
        comp.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def _create_horizontal_layout(
        self, matryoshkas: List[MatryoshkaData]
    ) -> io.BytesIO:
        """Горизонтальное расположение матрешек с адаптивной шириной холста"""
        images = []
        for data in matryoshkas:
            params = {
                **self.global_config,
                "fill_percent": data.fill_percent,
                "fill_color": data.fill_color,
                "show_info": True,
                "title": data.title,
                "daily_amount": data.daily_amount,
                "day": data.day,
                "total_amount": data.total_amount,
                "plan_amount": data.plan_amount,
            }
            buf = (
                MatryoshkaFillBuilder(self.template_path)
                .configure(**params)
                .load_image()
                .find_boundaries()
                .create_fill_layer()
                .add_percentage_text()
                .add_info_text()
                .build()
            )
            images.append(Image.open(buf))

        widths = [img.width for img in images]
        heights = [img.height for img in images]
        comp_w = sum(widths) + self.padding * (len(images) - 1)
        comp_h = max(heights)

        comp = Image.new("RGBA", (comp_w, comp_h), (250, 250, 250, 255))

        x = 0
        for img in images:
            comp.paste(img, (x, (comp_h - img.height) // 2), img)
            x += img.width + self.padding

        buf = io.BytesIO()
        comp.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def _create_grid_layout(self, matryoshkas: List[MatryoshkaData]) -> io.BytesIO:
        """Создание сетки из матрешек (для будущего расширения)"""

        return self._create_vertical_layout(matryoshkas)


def create_matryoshka_collection(
    template_path: str,
    shops_data: List[Dict[str, Any]],
    layout: str = "vertical",
    max_per_image: int = 2,
    output_dir: str = "",
) -> List[io.BytesIO]:
    """
    Фасад для создания коллекции изображений матрешек

    Args:
        template_path: Путь к шаблону матрешки
        shops_data: Список словарей с данными о магазинах
        layout: Тип расположения ('vertical', 'horizontal', 'grid')
        max_per_image: Максимальное количество матрешек на изображении
        output_dir: Директория для сохранения файлов

    Returns:
        Список буферов с изображениями
    """

    strategy_map = {
        "vertical": LayoutStrategy.VERTICAL,
        "horizontal": LayoutStrategy.HORIZONTAL,
        "grid": LayoutStrategy.GRID,
    }
    strategy = strategy_map.get(layout.lower(), LayoutStrategy.VERTICAL)

    matryoshkas_data = []
    for shop in shops_data:
        matryoshka = MatryoshkaData(
            fill_percent=shop.get("fill_percent", 40),
            title=shop.get("title", "Магазин"),
            daily_amount=shop.get("daily_amount", "0"),
            day=shop.get("day", "01"),
            total_amount=shop.get("total_amount", "0"),
            plan_amount=shop.get("plan_amount", "0"),
            fill_color=shop.get("fill_color", (70, 130, 180, 200)),
        )
        matryoshkas_data.append(matryoshka)

    builder = MatryoshkaCompositionBuilder(template_path)

    for data in matryoshkas_data:
        builder.add_matryoshka(data)

    buffers = (
        builder.set_layout(strategy).set_max_per_image(max_per_image).build(output_dir)
    )

    return buffers


if __name__ == "__main__":

    shops = [
        {
            "title": "Магазин №1",
            "fill_percent": 65,
            "daily_amount": "24 500",
            "day": "15.09.23",
            "total_amount": "187 450",
            "plan_amount": "300 000 000",
            "fill_color": (70, 130, 180, 200),
        },
        {
            "title": "Магазин №2",
            "fill_percent": 42,
            "daily_amount": "15 800",
            "day": "15.09.23",
            "total_amount": "126 340",
            "plan_amount": "300 000 000",
            "fill_color": (34, 139, 34, 200),
        },
        {
            "title": "Магазин №3",
            "fill_percent": 28,
            "daily_amount": "8 400",
            "day": "15.09.23",
            "total_amount": "84 200",
            "plan_amount": "300 000 000",
            "fill_color": (178, 34, 34, 200),
        },
    ]

    buffers = create_matryoshka_collection(
        "resources/matryoshka_template.png",
        shops,
        layout="vertical",
        max_per_image=2,
        output_dir="output",
    )

    print(f"Создано {len (buffers )} изображений с матрешками")

    if buffers:
        for idx, buffer in enumerate(buffers):
            img = Image.open(buffer)
            img.show(title=f"Матрешка {idx +1 }")
