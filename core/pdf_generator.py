"""
AlbumGenerator — Pixel-perfect school album PDF generator.

Uses Pillow + NumPy for green chromakey masking: photos are composited
ONLY where green pixels exist in the template backgrounds.

Zone coordinates are read from TemplateZone records in the database.
"""

import io
import os
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ══════════════════════════════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════════════════════════════

# Константа размера шрифта для 300 DPI печати
LABEL_FONT_SIZE = 36       # Фамилия + Имя ученика
TEACHER_FONT_SIZE = 30     # Подпись учителя
LABEL_COLOR = (45, 45, 45) # Тёмно-серый


def _get_font(size: int):
    for fp in [r'C:\Windows\Fonts\arial.ttf',
               r'C:\Windows\Fonts\times.ttf',
               '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if os.path.isfile(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def _get_font_bold(size: int):
    for fp in [r'C:\Windows\Fonts\arialbd.ttf',
               r'C:\Windows\Fonts\timesbd.ttf',
               '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.isfile(fp):
            return ImageFont.truetype(fp, size)
    return _get_font(size)


# ══════════════════════════════════════════════════════════════════════════════
#  ALBUM GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class AlbumGenerator:
    """
    Pixel-perfect school album generator.

    Template backgrounds contain green chromakey zones.  The generator
    reads zone coordinates from TemplateZone DB records, detects green
    pixels, and replaces them with the corresponding photo.
    """

    # ── Green chromakey thresholds ────────────────────────────────────────
    GREEN_CHANNEL_MIN = 80
    GREEN_DOMINANCE   = 25

    def __init__(self, album_order):
        self.order = album_order
        self.school_class = album_order.school_class
        self.template = album_order.template

        # Кеши
        self._students_cache = None
        self._group_photos_cache = None

    # ── Image I/O ────────────────────────────────────────────────────────

    @staticmethod
    def _open_image(image_field):
        if not image_field or not getattr(image_field, 'name', None):
            return None
        try:
            path = image_field.path
            if not os.path.isfile(path):
                return None
            return Image.open(path).convert('RGB')
        except Exception:
            return None

    def _open_bg(self, field, default_size=(5079, 3602)):
        img = self._open_image(field)
        return img if img else Image.new('RGB', default_size, (255, 255, 255))

    # ── Photo fitting (cover-mode: scale + center-crop) ──────────────────

    @staticmethod
    def _fit_cover(photo, target_w, target_h):
        w, h = photo.size
        scale = max(target_w / w, target_h / h)
        nw, nh = int(w * scale), int(h * scale)
        photo = photo.resize((nw, nh), Image.LANCZOS)
        left = (nw - target_w) // 2
        top  = (nh - target_h) // 2
        return photo.crop((left, top, left + target_w, top + target_h))

    # ── Chromakey green detection ────────────────────────────────────────

    def _detect_green_mask(self, region):
        """Return an 'L'-mode mask: white = green pixel, black = keep bg."""
        arr = np.array(region, dtype=np.int16)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        is_green = (
            (g > self.GREEN_CHANNEL_MIN) &
            (g > r + self.GREEN_DOMINANCE) &
            (g > b + self.GREEN_DOMINANCE)
        )
        return Image.fromarray((is_green.astype(np.uint8) * 255), 'L')

    def _paste_on_green(self, bg, photo, zone):
        """Composite *photo* onto *bg* — only green pixels are replaced."""
        x, y, w, h = zone
        # Clamp zone to image bounds
        bw, bh = bg.size
        w = min(w, bw - x)
        h = min(h, bh - y)
        if w <= 0 or h <= 0:
            return

        region = bg.crop((x, y, x + w, y + h))
        mask   = self._detect_green_mask(region)
        fitted = self._fit_cover(photo, w, h)
        result = Image.composite(fitted, region, mask)
        bg.paste(result, (x, y))

    # ── Text drawing ─────────────────────────────────────────────────────

    @staticmethod
    def _draw_label(draw, text, zone, font, color=LABEL_COLOR):
        """Draw centred text just below the zone."""
        x, y, w, h = zone
        lines = text.strip().split('\n')
        ty = y + h + 6
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((x + (w - tw) // 2, ty), line, fill=color, font=font)
            ty += th + 3

    # ── Data fetchers ────────────────────────────────────────────────────

    def _get_students(self):
        """Cached alphabetical student list."""
        if self._students_cache is None:
            self._students_cache = list(
                self.school_class.students.all().order_by('last_name', 'first_name')
            )
        return self._students_cache

    def _get_student_portrait(self, student):
        from .models import PhotoSelection, Photo
        try:
            sel = PhotoSelection.objects.get(student=student, is_confirmed=True)
            portrait = sel.selected_photos.filter(photo_type='portrait').first()
            if portrait:
                return self._open_image(portrait.image)
        except PhotoSelection.DoesNotExist:
            pass
        portrait = Photo.objects.filter(
            student=student, photo_type='portrait'
        ).first()
        if portrait:
            return self._open_image(portrait.image)
        return None

    def _get_group_photos(self):
        """Get group photos: from zone_assignments or auto-detected."""
        if self._group_photos_cache is not None:
            return self._group_photos_cache

        from .models import Photo
        photos = list(Photo.objects.filter(
            school_class=self.school_class, photo_type='group'
        ))
        self._group_photos_cache = photos
        return photos

    def _get_photo_for_zone(self, zone, student_index=0):
        """
        Determine which photo to paste into a given zone.

        Args:
            zone: TemplateZone instance
            student_index: for student zones, which student (by alphabetical order)

        Returns:
            PIL Image or None
        """
        from .models import Photo

        zone_type = zone.zone_type
        assignments = self.order.zone_assignments or {}
        assigned_photo_id = assignments.get(str(zone.id))

        # Если фото явно назначено в заказе — используем его
        if assigned_photo_id:
            try:
                photo = Photo.objects.get(id=assigned_photo_id)
                return self._open_image(photo.image)
            except Photo.DoesNotExist:
                pass

        # Иначе — автоматическая логика по типу зоны
        if zone_type == 'teacher':
            return self._open_image(self.school_class.teacher_photo)

        elif zone_type == 'student':
            students = self._get_students()
            if student_index < len(students):
                return self._get_student_portrait(students[student_index])
            return None

        elif zone_type == 'group':
            group_photos = self._get_group_photos()
            if group_photos:
                # Берём по sort_order (round-robin если не хватает)
                idx = zone.sort_order % len(group_photos) if group_photos else 0
                if idx < len(group_photos):
                    return self._open_image(group_photos[idx].image)
            return None

        elif zone_type == 'hero':
            # hero заполняется отдельно через render_spread (target_student)
            return None

        return None

    # ══════════════════════════════════════════════════════════════════════
    #  RENDER SPREAD (universal)
    # ══════════════════════════════════════════════════════════════════════

    def render_spread(self, spread, target_student=None):
        """
        Render one spread: paste photos into all zones.

        Args:
            spread: TemplateSpread instance
            target_student: Student instance (for cover hero portrait)

        Returns:
            PIL Image
        """
        default_size = (spread.bg_width or 5079, spread.bg_height or 3602)
        bg = self._open_bg(spread.background, default_size)
        draw = ImageDraw.Draw(bg)

        name_font = _get_font_bold(LABEL_FONT_SIZE)
        teacher_font = _get_font(TEACHER_FONT_SIZE)

        zones = spread.zones.all().order_by('sort_order')

        # Для student-зон нужен отдельный счётчик
        student_counter = 0
        # Для group-зон — глобальный счётчик по всем развороQтам
        # (будет управляться извне через sort_order)

        students = self._get_students()

        for zone in zones:
            zone_rect = (zone.x, zone.y, zone.w, zone.h)

            if zone.zone_type == 'hero':
                # Портрет «героя» альбома (текущий ученик)
                if target_student:
                    hero_img = self._get_student_portrait(target_student)
                    if hero_img:
                        self._paste_on_green(bg, hero_img, zone_rect)

            elif zone.zone_type == 'teacher':
                teacher_img = self._open_image(self.school_class.teacher_photo)
                if teacher_img:
                    self._paste_on_green(bg, teacher_img, zone_rect)
                teacher_name = self.school_class.teacher_name or 'Учитель'
                self._draw_label(draw, teacher_name, zone_rect, teacher_font)

            elif zone.zone_type == 'student':
                # sort_order определяет какой ученик по алфавиту
                idx = zone.sort_order
                # Для виньетки: если sort_order=0 — это teacher (уже обработан),
                # student зоны начинаются с sort_order 1+ :
                # Но мы назначаем sort_order отдельно, поэтому используем student_counter
                if student_counter < len(students):
                    student = students[student_counter]
                    portrait = self._get_student_portrait(student)
                    if portrait:
                        self._paste_on_green(bg, portrait, zone_rect)
                    label = f"{student.last_name}\n{student.first_name}"
                    self._draw_label(draw, label, zone_rect, name_font)
                student_counter += 1

            elif zone.zone_type == 'group':
                photo = self._get_photo_for_zone(zone)
                if photo:
                    self._paste_on_green(bg, photo, zone_rect)

        return bg

    # ══════════════════════════════════════════════════════════════════════
    #  PDF GENERATION
    # ══════════════════════════════════════════════════════════════════════

    def generate_individual_pdf(self, target_student):
        """Build a multi-spread PDF for one student → bytes."""
        spreads_images = []

        # Получаем все развороты шаблона, упорядоченные
        template_spreads = self.template.spreads.all().order_by('spread_order')

        for spread in template_spreads:
            img = self.render_spread(spread, target_student=target_student)
            spreads_images.append(img)

        if not spreads_images:
            spreads_images = [Image.new('RGB', (5079, 3602), 'white')]

        buf = io.BytesIO()
        spreads_images[0].save(
            buf, format='PDF', save_all=True,
            append_images=spreads_images[1:], resolution=300.0,
        )
        buf.seek(0)
        return buf.read()

    # ══════════════════════════════════════════════════════════════════════
    #  ZIP GENERATION (one PDF per student)
    # ══════════════════════════════════════════════════════════════════════

    def generate_class_zip(self):
        students = self.school_class.students.all().order_by(
            'last_name', 'first_name'
        )
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for student in students:
                pdf = self.generate_individual_pdf(student)
                zf.writestr(
                    f"Album_{student.last_name}_{student.first_name}.pdf",
                    pdf,
                )
        zip_buf.seek(0)
        return zip_buf.read()
