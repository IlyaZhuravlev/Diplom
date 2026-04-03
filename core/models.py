from django.db import models
import string
import random


def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))


# ═══════════════════════════════════════════════════════════════════════════════
#  ШКОЛЫ И КЛАССЫ
# ═══════════════════════════════════════════════════════════════════════════════

class School(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    address = models.CharField(max_length=500, verbose_name="Адрес", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Школа"
        verbose_name_plural = "Школы"


class SchoolClass(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classes", verbose_name="Школа")
    name = models.CharField(max_length=10, verbose_name="Название/буква класса")
    graduation_year = models.IntegerField(verbose_name="Год выпуска")
    parent_password = models.CharField(max_length=50, default=generate_random_password, verbose_name="Пароль для родителей")
    teacher_name = models.CharField(max_length=150, verbose_name="ФИО классного руководителя", blank=True, default="Классный руководитель")
    teacher_photo = models.ImageField(upload_to='schools/teachers/', verbose_name="Фото классного руководителя", null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.graduation_year}) - {self.school.name}"

    class Meta:
        verbose_name = "Класс"
        verbose_name_plural = "Классы"


# ═══════════════════════════════════════════════════════════════════════════════
#  УЧЕНИКИ И ФОТО
# ═══════════════════════════════════════════════════════════════════════════════

class Student(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="students", verbose_name="Класс")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Ученик"
        verbose_name_plural = "Ученики"


class Photo(models.Model):
    TYPE_CHOICES = (
        ('portrait', 'Портрет'),
        ('group', 'Групповое'),
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="photos", verbose_name="Класс")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, related_name="photos", verbose_name="Ученик")
    image = models.ImageField(upload_to='photos/', verbose_name="Фотография")
    photo_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Тип фото")

    def __str__(self):
        student_str = f" ({self.student})" if self.student else " (Общее)"
        return f"{self.get_photo_type_display()}{student_str} - {self.school_class.name}"

    class Meta:
        verbose_name = "Фотография"
        verbose_name_plural = "Фотографии"


class PhotoSelection(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="photo_selection", verbose_name="Ученик")
    selected_photos = models.ManyToManyField(Photo, related_name="selections", verbose_name="Выбранные фото")
    is_confirmed = models.BooleanField(default=False, verbose_name="Подтверждено")

    def __str__(self):
        return f"Выбор фото: {self.student}"

    class Meta:
        verbose_name = "Выбор фото"
        verbose_name_plural = "Выборы фото"


class Shoot(models.Model):
    STATUS_CHOICES = (
        ('planned', 'Запланирована'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="shoots", verbose_name="Класс")
    date = models.DateField(verbose_name="Дата")
    time = models.TimeField(verbose_name="Время")
    description = models.TextField(blank=True, verbose_name="Описание")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name="Статус")

    def __str__(self):
        return f"Съемка {self.school_class.name} ({self.date})"

    class Meta:
        verbose_name = "Съемка"
        verbose_name_plural = "Съемки"


# ═══════════════════════════════════════════════════════════════════════════════
#  ШАБЛОНЫ АЛЬБОМОВ (динамическая структура)
# ═══════════════════════════════════════════════════════════════════════════════

class AlbumTemplate(models.Model):
    """Шаблон альбома — контейнер для разворотов."""
    name = models.CharField(max_length=255, verbose_name="Название")

    def __str__(self):
        spread_count = self.spreads.count()
        return f"{self.name} ({spread_count} развор.)"

    class Meta:
        verbose_name = "Шаблон альбома"
        verbose_name_plural = "Шаблоны альбомов"


class TemplateSpread(models.Model):
    """Один разворот (2 страницы) шаблона альбома."""
    SPREAD_TYPES = (
        ('cover', 'Обложка'),
        ('vignette', 'Виньетка (класс)'),
        ('group', 'Групповые фото'),
    )
    template = models.ForeignKey(
        AlbumTemplate, on_delete=models.CASCADE,
        related_name='spreads', verbose_name="Шаблон"
    )
    spread_order = models.PositiveIntegerField(
        verbose_name="Порядок", default=1,
        help_text="1 = обложка, 2 = виньетка, 3-5 = групповые"
    )
    spread_type = models.CharField(
        max_length=20, choices=SPREAD_TYPES,
        verbose_name="Тип разворота"
    )
    background = models.ImageField(
        upload_to='templates/backgrounds/',
        verbose_name="Фоновое изображение"
    )
    bg_width = models.PositiveIntegerField(
        verbose_name="Ширина фона (px)", default=0,
        help_text="Заполняется автоматически"
    )
    bg_height = models.PositiveIntegerField(
        verbose_name="Высота фона (px)", default=0,
        help_text="Заполняется автоматически"
    )

    def save(self, *args, **kwargs):
        # Автоматически определяем размеры фона при сохранении
        if self.background:
            try:
                from PIL import Image as PILImage
                img = PILImage.open(self.background)
                self.bg_width, self.bg_height = img.size
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.template.name} — Разворот {self.spread_order} ({self.get_spread_type_display()})"

    class Meta:
        verbose_name = "Разворот шаблона"
        verbose_name_plural = "Развороты шаблонов"
        ordering = ['template', 'spread_order']
        unique_together = [['template', 'spread_order']]


class TemplateZone(models.Model):
    """Зона на развороте, куда вставляется фотография."""
    ZONE_TYPES = (
        ('hero', 'Портрет героя (обложка)'),
        ('teacher', 'Учитель'),
        ('student', 'Ученик (виньетка)'),
        ('group', 'Групповое фото'),
    )
    spread = models.ForeignKey(
        TemplateSpread, on_delete=models.CASCADE,
        related_name='zones', verbose_name="Разворот"
    )
    zone_type = models.CharField(
        max_length=20, choices=ZONE_TYPES,
        verbose_name="Тип зоны"
    )
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name="Порядок сортировки",
        help_text="Для учеников: определяет какой по алфавиту ребёнок попадёт в эту зону"
    )
    # Координаты в пикселях оригинального фонового изображения
    x = models.PositiveIntegerField(verbose_name="X (px)")
    y = models.PositiveIntegerField(verbose_name="Y (px)")
    w = models.PositiveIntegerField(verbose_name="Ширина (px)")
    h = models.PositiveIntegerField(verbose_name="Высота (px)")

    def __str__(self):
        return f"{self.get_zone_type_display()} #{self.sort_order} @ ({self.x},{self.y} {self.w}×{self.h})"

    class Meta:
        verbose_name = "Зона шаблона"
        verbose_name_plural = "Зоны шаблонов"
        ordering = ['spread', 'sort_order']


# ═══════════════════════════════════════════════════════════════════════════════
#  ЗАКАЗЫ АЛЬБОМОВ
# ═══════════════════════════════════════════════════════════════════════════════

class AlbumOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('generating', 'Генерация...'),
        ('ready', 'Готов'),
        ('error', 'Ошибка'),
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE,
        related_name="album_orders", verbose_name="Класс"
    )
    template = models.ForeignKey(
        AlbumTemplate, on_delete=models.PROTECT,
        verbose_name="Шаблон"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='draft', verbose_name="Статус"
    )

    # Привязки фото к зонам: { "<zone_id>": <photo_id>, ... }
    zone_assignments = models.JSONField(
        default=dict, blank=True,
        verbose_name="Привязки фото к зонам",
        help_text='Формат: {"<zone_id>": <photo_id>, ...}'
    )

    pdf_file = models.FileField(
        upload_to='albums/', verbose_name="PDF-файл", blank=True
    )
    zip_file = models.FileField(
        upload_to='albums/', verbose_name="ZIP-архив", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Заказ: {self.school_class} — {self.template.name}"

    class Meta:
        verbose_name = "Заказ альбома"
        verbose_name_plural = "Заказы альбомов"
        ordering = ['-created_at']
