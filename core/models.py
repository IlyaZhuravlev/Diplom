from django.db import models
import string
import random

def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

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

    def __str__(self):
        return f"{self.name} ({self.graduation_year}) - {self.school.name}"
    
    class Meta:
        verbose_name = "Класс"
        verbose_name_plural = "Классы"

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


class AlbumTemplate(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    page_count = models.PositiveIntegerField(verbose_name="Количество страниц", default=5)
    # ── Новые поля для ландшафтных разворотов ──
    oblozhka_spread_template = models.TextField(
        verbose_name="HTML-разворот ОБЛОЖКИ (478×330mm)",
        blank=True,
        help_text="Jinja2 HTML. @page { size: 478mm 330mm landscape; }. Переменные: {{ class_name }}, {{ school_name }}, {{ year }}, {{ cover_image_url }}",
    )
    hero_spread_template = models.TextField(
        verbose_name="HTML-разворот VIP-ученика (430×350mm)",
        blank=True,
        help_text="Jinja2 HTML. @page { size: 430mm 350mm landscape; }. Переменные: {{ hero.full_name }}, {{ hero.photo_url }}, {{ class_name }}",
    )
    grid_spread_template = models.TextField(
        verbose_name="HTML-разворот СЕТКИ КЛАССА (430×350mm)",
        blank=True,
        help_text="Jinja2 HTML. @page { size: 430mm 350mm landscape; }. Переменные: {{ students }}, {{ class_name }}, {{ empty_cells }}, {{ range }}",
    )
    # ── Фоновые изображения для разворотов ──
    oblozhka_bg = models.ImageField(
        upload_to='templates/backgrounds/', verbose_name="Фон: Разворот обложки",
        null=True, blank=True,
    )
    hero_spread_bg = models.ImageField(
        upload_to='templates/backgrounds/', verbose_name="Фон: Разворот VIP-ученика",
        null=True, blank=True,
    )
    grid_spread_bg = models.ImageField(
        upload_to='templates/backgrounds/', verbose_name="Фон: Разворот сетки класса",
        null=True, blank=True,
    )

    def __str__(self):
        return f"{self.name} ({self.page_count} стр.)"

    class Meta:
        verbose_name = "Шаблон альбома"
        verbose_name_plural = "Шаблоны альбомов"


class AlbumOrder(models.Model):
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="album_orders", verbose_name="Класс"
    )
    template = models.ForeignKey(
        AlbumTemplate, on_delete=models.PROTECT, verbose_name="Шаблон"
    )
    cover_image = models.ImageField(
        upload_to='album_covers/', verbose_name="Обложка", blank=True
    )
    group_photo_1 = models.ForeignKey(
        Photo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="album_group1", verbose_name="Групповое фото 1"
    )
    group_photo_2 = models.ForeignKey(
        Photo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="album_group2", verbose_name="Групповое фото 2"
    )
    pdf_file = models.FileField(
        upload_to='albums/', verbose_name="PDF-файл", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Заказ: {self.school_class} — {self.template.name}"

    class Meta:
        verbose_name = "Заказ альбома"
        verbose_name_plural = "Заказы альбомов"
        ordering = ['-created_at']
