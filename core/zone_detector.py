"""
zone_detector.py — Автоматическое обнаружение зелёных зон на фоновом изображении.

Алгоритм:
1. Считываем изображение через Pillow
2. Детектим зелёные пиксели (g > 80, g > r+25, g > b+25)
3. BFS flood-fill для нахождения связных компонент
4. Фильтруем по площади (min_area)
5. Возвращаем координаты (x, y, w, h), отсортированные top→bottom, left→right
"""

import numpy as np
from PIL import Image


# Пороги для зелёного хромакея
GREEN_CHANNEL_MIN = 80
GREEN_DOMINANCE = 25
DEFAULT_MIN_AREA = 5000   # минимальная площадь зоны в пикселях


def detect_green_zones(image_path_or_file, min_area=DEFAULT_MIN_AREA):
    """
    Обнаруживает все зелёные зоны на изображении.

    Args:
        image_path_or_file: путь к файлу или file-like объект
        min_area: минимальная площадь зоны (в пикселях) для фильтрации шума

    Returns:
        list of (x, y, w, h) — координаты обнаруженных зон,
        отсортированные top→bottom, left→right
    """
    img = Image.open(image_path_or_file).convert('RGB')
    arr = np.array(img, dtype=np.int16)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Бинарная маска зелёных пикселей
    mask = (
        (g > GREEN_CHANNEL_MIN) &
        (g > r + GREEN_DOMINANCE) &
        (g > b + GREEN_DOMINANCE)
    ).astype(np.uint8)

    # Даунскейл для ускорения BFS (в 4 раза)
    scale = 4
    small = mask[::scale, ::scale]
    sh, sw = small.shape

    visited = np.zeros_like(small, dtype=bool)
    zones = []

    for sy in range(sh):
        for sx in range(sw):
            if small[sy, sx] and not visited[sy, sx]:
                # BFS flood-fill
                stack = [(sy, sx)]
                visited[sy, sx] = True
                min_y, max_y = sy, sy
                min_x, max_x = sx, sx
                count = 0

                while stack:
                    cy, cx = stack.pop()
                    count += 1
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < sh and 0 <= nx < sw and not visited[ny, nx] and small[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
                            min_y = min(min_y, ny)
                            max_y = max(max_y, ny)
                            min_x = min(min_x, nx)
                            max_x = max(max_x, nx)

                area = count * scale * scale
                if area >= min_area:
                    x = min_x * scale
                    y = min_y * scale
                    w = (max_x - min_x + 1) * scale
                    h = (max_y - min_y + 1) * scale
                    zones.append((x, y, w, h, area))

    # Сортировка: сверху вниз (y), слева направо (x)
    zones.sort(key=lambda z: (z[1], z[0]))
    return [(x, y, w, h) for x, y, w, h, _ in zones]


def auto_assign_zone_types(spread_type, zones):
    """
    Автоматически назначает типы зонам на основе типа разворота.

    Args:
        spread_type: 'cover' | 'vignette' | 'group'
        zones: list of (x, y, w, h)

    Returns:
        list of dict: [{'x', 'y', 'w', 'h', 'zone_type', 'sort_order'}, ...]
    """
    result = []

    if spread_type == 'cover':
        for i, (x, y, w, h) in enumerate(zones):
            result.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'zone_type': 'hero',
                'sort_order': i,
            })

    elif spread_type == 'vignette':
        for i, (x, y, w, h) in enumerate(zones):
            if i == 0:
                zone_type = 'teacher'
            else:
                zone_type = 'student'
            result.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'zone_type': zone_type,
                'sort_order': i,
            })

    elif spread_type == 'group':
        for i, (x, y, w, h) in enumerate(zones):
            result.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'zone_type': 'group',
                'sort_order': i,
            })

    return result


def detect_and_create_zones(spread_instance):
    """
    Высокоуровневая функция: детектит зелёные зоны на фоне разворота
    и создаёт записи TemplateZone в БД.

    Args:
        spread_instance: экземпляр TemplateSpread

    Returns:
        int: количество созданных зон
    """
    from .models import TemplateZone

    if not spread_instance.background:
        return 0

    # Удаляем старые зоны этого разворота
    spread_instance.zones.all().delete()

    # Детектим зоны
    raw_zones = detect_green_zones(spread_instance.background.path)

    # Назначаем типы
    typed_zones = auto_assign_zone_types(spread_instance.spread_type, raw_zones)

    # Создаём записи в БД
    created = []
    for zone_data in typed_zones:
        created.append(TemplateZone(
            spread=spread_instance,
            zone_type=zone_data['zone_type'],
            sort_order=zone_data['sort_order'],
            x=zone_data['x'],
            y=zone_data['y'],
            w=zone_data['w'],
            h=zone_data['h'],
        ))

    TemplateZone.objects.bulk_create(created)
    return len(created)
