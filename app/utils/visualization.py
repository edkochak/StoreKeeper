from typing import Dict, Any
import matplotlib.pyplot as plt


def generate_matryoshka_image(data: Dict[str, Any]) -> bytes:
    """
    Генерирует изображение матрешки на основе данных о выполнении плана.
    
    Args:
        data: Словарь с данными о выполнении плана
        
    Returns:
        bytes: Байты PNG-изображения
    """
    title = data.get("title", "Магазин")
    fill_percent = data.get("fill_percent", 0)
    daily_amount = data.get("daily_amount", "0")
    day = data.get("day", "01.01.00")
    total_amount = data.get("total_amount", "0")
    plan_amount = data.get("plan_amount", "0")
    
    # Создаем фигуру и оси
    fig, ax = plt.subplots(figsize=(8, 12))
    
    # Настройка шрифтов - УВЕЛИЧИВАЕМ РАЗМЕР ТЕКСТА
    plt.rcParams['font.size'] = 14  # Базовый размер шрифта
    title_font = {'fontsize': 18, 'fontweight': 'bold'}  # Заголовок крупным шрифтом
    text_font = {'fontsize': 16}  # Основной текст увеличенным шрифтом
    
    # Рисуем матрешку
    # ...existing code...
    
    # Добавляем заголовок (название магазина)
    ax.text(0.5, 0.95, title, ha='center', va='top', transform=ax.transAxes, **title_font)
    
    # Добавляем информацию о прогрессе выполнения плана
    progress_text = f"{fill_percent}% от плана"
    ax.text(0.5, 0.85, progress_text, ha='center', va='center', transform=ax.transAxes, **text_font)
    
    # Добавляем информацию о сумме за день
    day_text = f"За {day}: {daily_amount}"
    ax.text(0.5, 0.2, day_text, ha='center', va='center', transform=ax.transAxes, **text_font)
    
    # Добавляем информацию о выполнении плана
    plan_text = f"План: {plan_amount}"
    ax.text(0.5, 0.12, plan_text, ha='center', va='center', transform=ax.transAxes, **text_font)
    
    # Добавляем информацию о текущем итоге
    total_text = f"Итого: {total_amount}"
    ax.text(0.5, 0.05, total_text, ha='center', va='center', transform=ax.transAxes, **text_font)
    
    # Сохраняем изображение в байты
    from io import BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    return buffer.getvalue()