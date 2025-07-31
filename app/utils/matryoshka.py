import io
import os
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont


# 3D render function (adapted from test.py)
def render_model_with_fill(
    file_path: str,
    percentage: float,
    fill_color: Tuple[int, int, int, int],
    window_size: Tuple[int, int] = (1024, 1024),
) -> Optional[Image.Image]:
    """
    Загружает 3D-модель, заполняет её и возвращает изображение в виде объекта PIL.Image.
    """
    if not 0 <= percentage <= 100:
        print(f"Ошибка: Процент должен быть в диапазоне от 0 до 100. Меняю на 0/100: {percentage}")
        percentage = max(0, min(percentage, 100))

    try:
        mesh = pv.read(file_path)
    except Exception as e:
        print(f"Не удалось загрузить файл {file_path}: {e}")
        return None

    # Центрируем модель и настраиваем камеру
    mesh.translate(-np.array(mesh.center), inplace=True)

    bounds = mesh.bounds
    y_min, y_max = bounds[2], bounds[3]
    height = y_max - y_min

    if height == 0:
        print("Невозможно определить высоту модели для отсечения.")
        return None

    fill_height = y_min + (height * percentage / 100.0)
    clip_origin = [mesh.center[0], fill_height, mesh.center[2]]
    clip_normal = [0, 1, 0]

    filled_part = mesh.clip(normal=clip_normal, origin=clip_origin, invert=True)
    unfilled_part = mesh.clip(normal=clip_normal, origin=clip_origin, invert=False)

    plotter = pv.Plotter(off_screen=True, window_size=window_size, image_scale=1)
    plotter.background_color = (250, 250, 250, 255)  # Match background of composition

    rgb_color = fill_color[:3]
    opacity = fill_color[3] / 255.0 if len(fill_color) == 4 else 1.0

    plotter.add_mesh(filled_part, color=rgb_color, opacity=opacity, style="surface")
    plotter.add_mesh(unfilled_part, color="beige", style="surface")

    plotter.camera_position = "xy"
    plotter.camera.elevation = 15
    plotter.camera.azimuth = 15

    img_array = plotter.screenshot(
        return_img=True, transparent_background=True, window_size=window_size
    )  # Use transparent background
    plotter.close()

    if img_array is not None:
        return Image.fromarray(img_array)
    return None


class MatryoshkaFillBuilder:
    """
    Построитель (Builder) для создания изображений с заливкой 3D-модели.
    """

    def __init__(self, model_path: str):
        """Инициализация с путем к 3D-модели"""
        self.model_path = model_path
        self.result: Optional[Image.Image] = None
        self.config = {
            "fill_percent": 40,
            "fill_color": (70, 130, 180, 200),
            "show_percent": True,
            "font_size": 50,
            "show_info": False,
            "title": "Название",
            "daily_amount": "0",
            "day": "01",
            "total_amount": "0",
            "plan_amount": "0",
            "info_text_color": (0, 0, 0, 255),
            "info_font_size": 36,
            "info_x_offset": 50,
            "render_size": (1000, 1000),
        }

    def configure(self, **kwargs):
        """Настройка параметров"""
        self.config.update(kwargs)
        return self

    def render_model(self):
        """Рендеринг 3D-модели"""
        self.result = render_model_with_fill(
            self.model_path,
            self.config["fill_percent"],
            self.config["fill_color"],
            self.config["render_size"],
        )
        return self

    def add_percentage_text(self):
        """Добавление текста с процентом заполнения"""
        if not self.config["show_percent"] or self.result is None:
            return self

        draw = ImageDraw.Draw(self.result)
        percent_text = f"{round(self.config['fill_percent'])}%"

        try:
            font = ImageFont.truetype("resources/arialmt.ttf", self.config["font_size"])
        except IOError:
            font = ImageFont.load_default()

        text_x, text_y = 20, 20
        text_color = self.config["fill_color"][:3] + (255,)
        padding = 5

        text_bbox = draw.textbbox((text_x, text_y), percent_text, font=font)
        bg_bbox = (
            text_bbox[0] - padding,
            text_bbox[1] - padding,
            text_bbox[2] + padding,
            text_bbox[3] + padding,
        )

        # Create a temporary layer for the text background
        bg_layer = Image.new("RGBA", self.result.size, (255, 255, 255, 0))
        bg_draw = ImageDraw.Draw(bg_layer)
        bg_draw.rectangle(bg_bbox, fill=(250, 250, 250, 180))

        # Composite the background layer with the result
        self.result = Image.alpha_composite(self.result, bg_layer)

        # Draw the text on top of the composited image
        final_draw = ImageDraw.Draw(self.result)
        final_draw.text((text_x, text_y), percent_text, font=font, fill=text_color)

        return self

    def add_info_text(self):
        """Добавление информационного текста справа от модели"""
        if not self.config["show_info"] or self.result is None:
            return self

        original_width, original_height = self.result.size
        info_panel_width = 950
        new_width = original_width + info_panel_width

        # Create a new canvas with a solid background color
        new_image = Image.new(
            "RGBA", (new_width, original_height), (250, 250, 250, 255)
        )
        # Paste the transparent render onto the new canvas
        new_image.paste(self.result, (0, 0), self.result)
        self.result = new_image

        draw = ImageDraw.Draw(self.result)

        try:
            title_font = ImageFont.truetype(
                "resources/arialmt.ttf", self.config["info_font_size"] + 4
            )
            normal_font = ImageFont.truetype("resources/arialmt.ttf", self.config["info_font_size"])
            bold_font = ImageFont.truetype(
                "resources/arialmt.ttf", self.config["info_font_size"]
            )
        except IOError:
            title_font = normal_font = bold_font = ImageFont.load_default()

        text_x = original_width + self.config["info_x_offset"]
        text_y = 50
        text_color = self.config["info_text_color"]

        draw.text(
            (text_x, text_y), self.config["title"], font=title_font, fill=text_color
        )
        text_y += int(self.config["info_font_size"] * 1.5)

        amount_day_text = f'{self.config["daily_amount"]} - {self.config["day"]}'
        draw.text((text_x, text_y), amount_day_text, font=normal_font, fill=text_color)
        text_y += int(self.config["info_font_size"] * 1.8)

        draw.text((text_x, text_y), "ТОТАЛ", font=bold_font, fill=text_color)
        text_y += int(self.config["info_font_size"] * 1.2)

        total_text = f'{self.config["total_amount"]} / {self.config["plan_amount"]}'
        draw.text((text_x, text_y), total_text, font=normal_font, fill=text_color)

        return self

    def build(self, output_path: Optional[str] = None) -> io.BytesIO:
        """Финальная сборка и возврат результата"""
        self.render_model()
        if self.result is None:
            return io.BytesIO()

        if self.config.get("show_info", False):
            self.add_info_text()

        # Percentage text should be added after info text, as info text re-creates the canvas
        if self.config.get("show_percent", True):
            self.add_percentage_text()

        if output_path:
            self.result.save(output_path)

        img_buffer = io.BytesIO()
        self.result.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer


class LayoutStrategy(Enum):
    VERTICAL = auto()
    HORIZONTAL = auto()
    GRID = auto()


class MatryoshkaData:
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
    def __init__(self, template_model_path: str):
        self.template_path = template_model_path
        self.matryoshkas: List[MatryoshkaData] = []
        self.layout_strategy = LayoutStrategy.VERTICAL
        self.max_per_image = 2
        self.padding = 10
        self.global_config = {
            "show_percent": True,
            "font_size": 50,
            "info_font_size": 40,
            "info_x_offset": 50,
            "render_size": (1000, 1000),
        }

    def add_matryoshka(self, data: MatryoshkaData) -> "MatryoshkaCompositionBuilder":
        self.matryoshkas.append(data)
        return self

    def set_layout(self, strategy: LayoutStrategy) -> "MatryoshkaCompositionBuilder":
        self.layout_strategy = strategy
        return self

    def set_max_per_image(self, count: int) -> "MatryoshkaCompositionBuilder":
        self.max_per_image = count
        return self

    def configure(self, **kwargs) -> "MatryoshkaCompositionBuilder":
        self.global_config.update(kwargs)
        return self

    def build(self, output_dir: str = "") -> List[io.BytesIO]:
        if not self.matryoshkas:
            return []

        groups = [
            self.matryoshkas[i : i + self.max_per_image]
            for i in range(0, len(self.matryoshkas), self.max_per_image)
        ]

        result_buffers = []
        layout_map = {
            LayoutStrategy.VERTICAL: self._create_vertical_layout,
            LayoutStrategy.HORIZONTAL: self._create_horizontal_layout,
            LayoutStrategy.GRID: self._create_grid_layout,
        }
        layout_func = layout_map.get(self.layout_strategy, self._create_vertical_layout)

        for idx, group in enumerate(groups):
            buffer = layout_func(group)
            if buffer.getbuffer().nbytes > 0:
                result_buffers.append(buffer)
                if output_dir:
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    file_path = os.path.join(output_dir, f"composition_{idx + 1}.png")
                    with open(file_path, "wb") as f:
                        f.write(buffer.getvalue())
        return result_buffers

    def _create_layout(
        self, matryoshkas: List[MatryoshkaData], is_vertical: bool
    ) -> io.BytesIO:
        images = []
        for data in matryoshkas:
            builder = MatryoshkaFillBuilder(self.template_path)
            config = self.global_config.copy()
            config.update(
                {
                    "fill_percent": data.fill_percent,
                    "title": data.title,
                    "daily_amount": data.daily_amount,
                    "day": data.day,
                    "total_amount": data.total_amount,
                    "plan_amount": data.plan_amount,
                    "fill_color": data.fill_color,
                    "show_info": True,
                }
            )
            img_buffer = builder.configure(**config).build()
            if img_buffer.getbuffer().nbytes > 0:
                images.append(Image.open(img_buffer))

        if not images:
            return io.BytesIO()

        widths, heights = zip(*(i.size for i in images))
        if is_vertical:
            total_width = max(widths)
            total_height = sum(heights) + self.padding * (len(images) - 1)
        else:
            total_width = sum(widths) + self.padding * (len(images) - 1)
            total_height = max(heights)

        comp = Image.new("RGBA", (total_width, total_height), (250, 250, 250, 255))
        current_pos = 0
        for img in images:
            if is_vertical:
                comp.paste(img, (0, current_pos))
                current_pos += img.height + self.padding
            else:
                comp.paste(img, (current_pos, 0))
                current_pos += img.width + self.padding

        buf = io.BytesIO()
        comp.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def _create_vertical_layout(self, matryoshkas: List[MatryoshkaData]) -> io.BytesIO:
        return self._create_layout(matryoshkas, is_vertical=True)

    def _create_horizontal_layout(
        self, matryoshkas: List[MatryoshkaData]
    ) -> io.BytesIO:
        return self._create_layout(matryoshkas, is_vertical=False)

    def _create_grid_layout(self, matryoshkas: List[MatryoshkaData]) -> io.BytesIO:
        # Placeholder for grid layout implementation
        print("Grid layout is not yet implemented.")
        return self._create_vertical_layout(matryoshkas)


def create_matryoshka_collection(
    template_path: str,
    shops_data: List[Dict[str, Any]],
    layout: str = "vertical",
    max_per_image: int = 2,
    output_dir: str = "",
) -> List[io.BytesIO]:
    strategy_map = {
        "vertical": LayoutStrategy.VERTICAL,
        "horizontal": LayoutStrategy.HORIZONTAL,
        "grid": LayoutStrategy.GRID,
    }
    strategy = strategy_map.get(layout.lower(), LayoutStrategy.VERTICAL)

    matryoshkas_data = [MatryoshkaData(**shop) for shop in shops_data]

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
            "fill_percent": 98,
            "daily_amount": "8 400",
            "day": "15.09.23",
            "total_amount": "294 200",
            "plan_amount": "300 000 000",
            "fill_color": (178, 34, 34, 200),
        },
    ]

    # Use the 3D model path
    model_path = "resources/bear3.glb"
    output_directory = "output"

    print(f"Создание изображений с 3D моделью из '{model_path}'...")

    buffers = create_matryoshka_collection(
        model_path,
        shops,
        layout="vertical",
        max_per_image=2,
        output_dir=output_directory,
    )

    print(f"Создано {len(buffers)} изображений в директории '{output_directory}'")
