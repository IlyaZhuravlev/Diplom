"""
AlbumGenerator — модуль генерации PDF-альбомов через WeasyPrint + Jinja2.

Архитектура: ландшафтные развороты (facing pages).
- Обложка:         478mm × 330mm landscape
- Внутренние стр.:  430mm × 350mm landscape

Использование:
    from core.pdf_generator import AlbumGenerator
    generator = AlbumGenerator(album_order)
    pdf_bytes = generator.generate_individual_pdf(student)
"""

import base64
import mimetypes
import os
import re
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from jinja2 import Template as Jinja2Template
from weasyprint import HTML


# ══════════════════════════════════════════════════════════════════════════════
#  ШАБЛОНЫ ПО УМОЛЧАНИЮ — ЛАНДШАФТНЫЕ РАЗВОРОТЫ
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_OBLOZHKA_SPREAD = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
@page { size: 478mm 330mm landscape; margin: 0; }
body { margin: 0; font-family: 'Arial', sans-serif; }
.spread {
    width: 478mm; height: 330mm;
    background: {% if bg_b64 %}url('{{ bg_b64 }}') center/cover no-repeat{% elif cover_image_b64 %}url('{{ cover_image_b64 }}') center/cover no-repeat{% else %}linear-gradient(135deg, #667eea 0%, #764ba2 100%){% endif %};
    display: flex; flex-direction: column; justify-content: flex-end;
    align-items: center; color: #fff; text-align: center;
    page-break-after: always;
}
.overlay {
    background: linear-gradient(transparent, rgba(0,0,0,0.65));
    width: 100%; padding: 60mm 20mm 50mm;
}
.spread h1 { font-size: 42pt; margin: 0 0 6mm; text-shadow: 0 2px 8px rgba(0,0,0,.4); }
.spread h2 { font-size: 24pt; margin: 0; font-weight: 300; opacity: .9; }
</style></head>
<body>
<div class="spread">
    <div class="overlay">
        <h1>{{ class_name }}</h1>
        <h2>{{ school_name }} — {{ year }}</h2>
    </div>
</div>
</body></html>
"""

DEFAULT_HERO_SPREAD = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
@page { size: 430mm 350mm landscape; margin: 0; }
body { margin: 0; font-family: 'Arial', sans-serif; }
.spread {
    width: 430mm; height: 350mm;
    display: flex; align-items: center; justify-content: center;
    background: {% if bg_b64 %}url('{{ bg_b64 }}') center/cover no-repeat{% else %}linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%){% endif %};
    text-align: center;
    page-break-after: always;
}
.hero-content {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
}
.hero-photo {
    width: 180mm; height: 240mm;
    object-fit: cover; border-radius: 5mm;
    box-shadow: 0 4px 30px rgba(0,0,0,.2);
}
.hero-placeholder {
    width: 180mm; height: 240mm;
    background: #e0e0e0; border-radius: 5mm;
    display: flex; align-items: center; justify-content: center;
    font-size: 36pt; color: #aaa;
}
.hero-name {
    margin-top: 12mm; font-size: 36pt; color: #333;
    font-weight: bold;
}
.hero-class {
    margin-top: 4mm; font-size: 18pt; color: #777;
}
</style></head>
<body>
<div class="spread">
    <div class="hero-content">
        {% if hero.photo_b64 %}<img class="hero-photo" src="{{ hero.photo_b64 }}" alt="{{ hero.full_name }}">
        {% else %}<div class="hero-placeholder">?</div>{% endif %}
        <div class="hero-name">{{ hero.full_name }}</div>
        <div class="hero-class">{{ class_name }}</div>
    </div>
</div>
</body></html>
"""

DEFAULT_GRID_SPREAD = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
@page { size: 430mm 350mm landscape; margin: 15mm; }
body { margin: 0; font-family: 'Arial', sans-serif; }
.spread {
    width: 400mm; height: 320mm;
    {% if bg_b64 %}background: url('{{ bg_b64 }}') center/cover no-repeat;{% endif %}
    page-break-after: always;
}
.header { text-align: center; margin-bottom: 8mm; color: #333; }
.header h2 { font-size: 18pt; margin: 0; }
.grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    grid-template-rows: repeat(4, 1fr);
    gap: 4mm;
    height: 290mm;
}
.cell {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    border: 0.3mm solid #e0e0e0; border-radius: 2mm;
    padding: 2mm; overflow: hidden;
}
.cell img {
    width: 100%; flex: 1; object-fit: cover;
    border-radius: 1.5mm;
}
.cell .name {
    font-size: 8pt; margin-top: 1mm; text-align: center;
    color: #444; line-height: 1.2;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 100%;
}
</style></head>
<body>
<div class="spread">
    <div class="header">
        <h2>{{ class_name }}</h2>
    </div>
    <div class="grid">
    {% for student in students %}
        <div class="cell">
            {% if student.photo_b64 %}<img src="{{ student.photo_b64 }}" alt="{{ student.full_name }}">
            {% else %}<div style="flex:1;background:#f0f0f0;width:100%;border-radius:1.5mm;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:12pt;">?</div>
            {% endif %}
            <div class="name">{{ student.full_name }}</div>
        </div>
    {% endfor %}
    {% for _ in range(empty_cells) %}
        <div class="cell" style="border-color:transparent;"></div>
    {% endfor %}
    </div>
</div>
</body></html>
"""


class AlbumGenerator:
    """Генератор PDF-альбомов — ландшафтные развороты."""

    # Сетка для grid-разворота (6 колонок × 4 ряда = 24 ученика на разворот)
    COLS = 6
    ROWS = 4

    def __init__(self, album_order):
        self.order = album_order
        self.school_class = album_order.school_class
        self.template = album_order.template

    # ── Утилиты ──────────────────────────────────────────────────────────

    @staticmethod
    def image_to_base64(image_field):
        """
        Читает ImageField с диска и возвращает data:image/...;base64,... строку.
        Если файла нет — возвращает пустую строку.
        """
        if not image_field or not image_field.name:
            return ''
        try:
            abs_path = image_field.path
            if not os.path.exists(abs_path):
                return ''
                
            mime_type, _ = mimetypes.guess_type(abs_path)
            if not mime_type:
                mime_type = 'image/jpeg'
                
            with open(abs_path, 'rb') as f:
                encoded_string = base64.b64encode(f.read()).decode('utf-8')
                
            return f'data:{mime_type};base64,{encoded_string}'
        except Exception:
            return ''

    # ── Валидация ─────────────────────────────────────────────────────────

    def validate(self):
        """
        Проверяет, что у каждого ученика класса есть подтверждённый выбор
        с хотя бы одним портретным фото. Возвращает список проблем.
        """
        from .models import PhotoSelection

        students = self.school_class.students.all().order_by('last_name', 'first_name')
        missing = []

        for student in students:
            try:
                selection = PhotoSelection.objects.get(student=student, is_confirmed=True)
                if not selection.selected_photos.filter(photo_type='portrait').exists():
                    missing.append(f"{student.last_name} {student.first_name} — нет портрета")
            except PhotoSelection.DoesNotExist:
                missing.append(f"{student.last_name} {student.first_name} — нет подтверждённого выбора")

        if missing:
            raise ValidationError(
                "Не все ученики готовы к генерации альбома:\n" + "\n".join(missing)
            )

    # ── Пагинация ─────────────────────────────────────────────────────────

    @classmethod
    def paginate(cls, items, cols=None, rows=None):
        """Разбивает список items на страницы по cols*rows элементов."""
        cols = cols or cls.COLS
        rows = rows or cls.ROWS
        per_page = cols * rows
        pages = []
        for i in range(0, len(items), per_page):
            pages.append(items[i:i + per_page])
        return pages

    # ── Подготовка данных учеников ────────────────────────────────────────

    def _get_student_data(self):
        """Возвращает отсортированный список словарей с данными учеников."""
        from .models import PhotoSelection

        students = self.school_class.students.all().order_by('last_name', 'first_name')
        result = []

        for student in students:
            photo_b64 = ''
            try:
                selection = PhotoSelection.objects.get(student=student, is_confirmed=True)
                portrait = selection.selected_photos.filter(photo_type='portrait').first()
                if portrait:
                    photo_b64 = self.image_to_base64(portrait.image)
            except PhotoSelection.DoesNotExist:
                pass

            result.append({
                'full_name': f"{student.last_name} {student.first_name}",
                'photo_b64': photo_b64,
            })

        return result

    # ── Рендеринг HTML ────────────────────────────────────────────────────

    def _render_template(self, template_str, default_str, context):
        """Рендерит Jinja2-шаблон (или дефолтный, если пустой)."""
        source = template_str.strip() if template_str else default_str
        tpl = Jinja2Template(source)
        return tpl.render(**context)

    # ── Сборка HTML-частей ────────────────────────────────────────────────

    @staticmethod
    def _extract_body_content(html):
        """Извлекает содержимое <body>…</body> из HTML-строки."""
        body_start = html.find('<body')
        body_end = html.find('</body>')
        if body_start == -1 or body_end == -1:
            return html
        content_start = html.find('>', body_start) + 1
        return html[content_start:body_end]

    @staticmethod
    def _extract_head_content(html):
        """Извлекает содержимое <head>…</head> из HTML-строки."""
        head_start = html.find('<head')
        head_end = html.find('</head>')
        if head_start == -1 or head_end == -1:
            return ''
        content_start = html.find('>', head_start) + 1
        return html[content_start:head_end]

    @classmethod
    def _combine_html_parts(cls, html_parts):
        """Собирает список HTML-документов в один с page-break между ними."""
        if not html_parts:
            return ''

        all_styles = []
        body_sections = []

        for part in html_parts:
            head = cls._extract_head_content(part)
            for m in re.finditer(r'<style[^>]*>(.*?)</style>', head, re.DOTALL):
                style = m.group(1).strip()
                if style and style not in all_styles:
                    all_styles.append(style)
            body_sections.append(cls._extract_body_content(part))

        combined = '<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8">\n'
        for style in all_styles:
            combined += f'<style>\n{style}\n</style>\n'
        combined += '</head>\n<body>\n'

        for idx, section in enumerate(body_sections):
            if idx > 0:
                combined += '<div style="page-break-before: always;"></div>\n'
            combined += section + '\n'

        combined += '</body>\n</html>'
        return combined

    # ── Генерация PDF (старый метод, оставлен для совместимости) ──────────

    def generate(self):
        """
        Главный метод: валидация → рендеринг → PDF → сохранение.
        Возвращает URL созданного PDF.
        """
        self.validate()
        # Генерируем PDF для первого ученика как fallback
        students = self.school_class.students.all().order_by('last_name', 'first_name')
        first_student = students.first()
        if not first_student:
            raise ValidationError("В классе нет учеников.")
        pdf_bytes = self.generate_individual_pdf(first_student)

        filename = f"album_{self.school_class.id}_{self.order.id}.pdf"
        self.order.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        return self.order.pdf_file.url

    # ── Генерация индивидуального PDF (ОСНОВНОЙ МЕТОД) ────────────────────

    def generate_individual_pdf(self, target_student):
        """
        Генерирует индивидуальный PDF-альбом для конкретного ученика.
        Порядок разворотов:
            1. Обложка        (oblozhka_spread_template, 478×330mm)
            2. VIP-ученик     (hero_spread_template, 430×350mm)
            3. Сетка класса   (grid_spread_template, 430×350mm)
        Возвращает bytes (PDF).
        """
        from .models import PhotoSelection

        html_parts = []

        # ── 1. Разворот обложки ──
        cover_image_b64 = self.image_to_base64(self.order.cover_image)
        oblozhka_bg_b64 = self.image_to_base64(self.template.oblozhka_bg)
        oblozhka_html = self._render_template(
            self.template.oblozhka_spread_template,
            DEFAULT_OBLOZHKA_SPREAD,
            {
                'class_name': str(self.school_class),
                'school_name': self.school_class.school.name,
                'year': self.school_class.graduation_year,
                'cover_image_b64': cover_image_b64,
                'bg_b64': oblozhka_bg_b64,
            },
        )
        html_parts.append(oblozhka_html)

        # ── 2. Разворот VIP-ученика ──
        hero_photo_b64 = ''
        try:
            selection = PhotoSelection.objects.get(student=target_student, is_confirmed=True)
            portrait = selection.selected_photos.filter(photo_type='portrait').first()
            if portrait:
                hero_photo_b64 = self.image_to_base64(portrait.image)
        except PhotoSelection.DoesNotExist:
            pass

        hero = {
            'full_name': f"{target_student.last_name} {target_student.first_name}",
            'photo_b64': hero_photo_b64,
        }
        hero_bg_b64 = self.image_to_base64(self.template.hero_spread_bg)
        hero_html = self._render_template(
            self.template.hero_spread_template,
            DEFAULT_HERO_SPREAD,
            {
                'hero': hero,
                'class_name': str(self.school_class),
                'bg_b64': hero_bg_b64,
            },
        )
        html_parts.append(hero_html)

        # ── 3. Разворот(ы) сетки класса ──
        student_data = self._get_student_data()
        pages_data = self.paginate(student_data)
        per_page = self.COLS * self.ROWS

        grid_bg_b64 = self.image_to_base64(self.template.grid_spread_bg)
        for page_students in pages_data:
            empty_cells = per_page - len(page_students)
            grid_html = self._render_template(
                self.template.grid_spread_template,
                DEFAULT_GRID_SPREAD,
                {
                    'students': page_students,
                    'class_name': str(self.school_class),
                    'empty_cells': empty_cells,
                    'range': range,
                    'bg_b64': grid_bg_b64,
                },
            )
            html_parts.append(grid_html)

        # ── Объединяем и генерируем PDF ──
        combined_html = self._combine_html_parts(html_parts)
        pdf_bytes = HTML(string=combined_html).write_pdf()
        return pdf_bytes
