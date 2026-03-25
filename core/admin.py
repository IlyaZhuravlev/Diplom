import io
import zipfile

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django import forms
from django.utils.html import format_html
from .models import School, SchoolClass, Student, Photo, PhotoSelection, Shoot, AlbumTemplate, AlbumOrder
from .utils import generate_class_album_pdf
from .pdf_generator import AlbumGenerator


# ═══════════════════════════════════════════════════════════════════════════════
#  ВИДЖЕТЫ И ФОРМЫ
# ═══════════════════════════════════════════════════════════════════════════════

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BulkUploadForm(forms.Form):
    school_class = forms.ModelChoiceField(queryset=SchoolClass.objects.all(), label="Класс")
    images = MultipleFileField(label="Фотографии", required=True)


class StudentForm(forms.ModelForm):
    bulk_photos = MultipleFileField(
        label="Массовая загрузка фото (Портреты)",
        required=False,
        help_text="Выберите несколько файлов. Они автоматически станут 'портретами' этого ученика.",
    )

    class Meta:
        model = Student
        fields = '__all__'


# ═══════════════════════════════════════════════════════════════════════════════
#  ДЕЙСТВИЯ (ACTIONS)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.action(description="📄 Сгенерировать выпускной альбом (PDF)")
def generate_class_album_action(modeladmin, request, queryset):
    from django.contrib import messages
    for school_class in queryset:
        students = school_class.students.all()
        confirmed_count = PhotoSelection.objects.filter(
            student__in=students, is_confirmed=True
        ).count()
        if confirmed_count < students.count():
            modeladmin.message_user(
                request,
                f"В классе {school_class} выбор сделали только "
                f"{confirmed_count} из {students.count()} учеников. Альбом неполный!",
                level=messages.WARNING,
            )

        pdf_url = generate_class_album_pdf(school_class.id)
        if pdf_url:
            modeladmin.message_user(
                request,
                format_html(
                    'Альбом для {}: <a href="{}" target="_blank"><b>Скачать PDF</b></a>',
                    school_class,
                    pdf_url,
                ),
                messages.SUCCESS,
            )
        else:
            modeladmin.message_user(request, "Ошибка при генерации.", messages.ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
#  ГРУППА: ШКОЛЫ И КЛАССЫ
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'graduation_year', 'student_count', 'parent_password')
    list_filter = ('school', 'graduation_year')
    search_fields = ('name', 'school__name')
    autocomplete_fields = ('school',)
    actions = [generate_class_album_action]
    ordering = ('school', 'name')

    @admin.display(description='Учеников')
    def student_count(self, obj):
        count = obj.students.count()
        return count

    # ── Кастомные URL-ы ──

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-upload/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='bulk_upload',
            ),
            path(
                '<path:object_id>/album-status/',
                self.admin_site.admin_view(self.album_status_view),
                name='album_status',
            ),
        ]
        return custom_urls + urls

    def album_status_view(self, request, object_id):
        school_class = self.get_object(request, object_id)
        students = school_class.students.all().order_by('last_name', 'first_name')

        status_list = []
        for student in students:
            is_done = PhotoSelection.objects.filter(student=student, is_confirmed=True).exists()
            status_list.append({'student': student, 'is_done': is_done})

        context = self.admin_site.each_context(request)
        context.update({
            'school_class': school_class,
            'status_list': status_list,
            'title': f'Статус альбома: {school_class.name}',
        })
        return render(request, "admin/album_status.html", context)

    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = BulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                school_class = form.cleaned_data['school_class']
                images = request.FILES.getlist('images')
                students = school_class.students.all()

                count_assigned = 0
                count_common = 0

                for image in images:
                    filename = image.name.lower()
                    assigned_student = None
                    for student in students:
                        if student.last_name.lower() in filename or student.first_name.lower() in filename:
                            assigned_student = student
                            break

                    if assigned_student:
                        Photo.objects.create(
                            school_class=school_class,
                            student=assigned_student,
                            image=image,
                            photo_type='portrait',
                        )
                        count_assigned += 1
                    else:
                        Photo.objects.create(
                            school_class=school_class,
                            student=None,
                            image=image,
                            photo_type='group',
                        )
                        count_common += 1

                self.message_user(
                    request,
                    f"Загружено {len(images)} фото. "
                    f"Привязано к ученикам: {count_assigned}, общих: {count_common}.",
                )
                return HttpResponseRedirect("../")
        else:
            form = BulkUploadForm()

        context = self.admin_site.each_context(request)
        context['form'] = form
        context['opts'] = self.model._meta
        context['title'] = "Массовая загрузка фотографий"
        return render(request, "admin/bulk_upload.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
#  ГРУППА: КЛИЕНТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentForm
    list_display = ('last_name', 'first_name', 'get_school', 'school_class')
    list_filter = ('school_class__school', 'school_class')
    search_fields = ('last_name', 'first_name')
    autocomplete_fields = ('school_class',)
    ordering = ('last_name', 'first_name')
    list_per_page = 30

    @admin.display(description='Школа', ordering='school_class__school__name')
    def get_school(self, obj):
        return obj.school_class.school if obj.school_class else '—'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        images = request.FILES.getlist('bulk_photos')
        count = 0
        for image in images:
            if image:
                Photo.objects.create(
                    school_class=obj.school_class,
                    student=obj,
                    image=image,
                    photo_type='portrait',
                )
                count += 1
        if count > 0:
            self.message_user(
                request,
                f"Дополнительно загружено и привязано {count} портретных фото для {obj}.",
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  ГРУППА: ПРОИЗВОДСТВО
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'photo_type', 'student', 'school_class', 'image_preview')
    list_filter = ('student__school_class__school', 'student__school_class', 'photo_type')
    search_fields = ('student__last_name', 'student__first_name')
    autocomplete_fields = ('student', 'school_class')
    list_per_page = 30

    @admin.display(description='Превью')
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px; border-radius:4px;" />',
                obj.image.url,
            )
        return '—'


@admin.register(PhotoSelection)
class PhotoSelectionAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_school', 'get_class', 'photos_count', 'is_confirmed')
    list_filter = (
        'is_confirmed',
        'student__school_class__school',
        'student__school_class',
    )
    search_fields = ('student__last_name', 'student__first_name')
    autocomplete_fields = ('student',)
    filter_horizontal = ('selected_photos',)
    list_per_page = 30

    @admin.display(description='Школа', ordering='student__school_class__school__name')
    def get_school(self, obj):
        return obj.student.school_class.school if obj.student and obj.student.school_class else '—'

    @admin.display(description='Класс', ordering='student__school_class__name')
    def get_class(self, obj):
        return obj.student.school_class if obj.student else '—'

    @admin.display(description='Фото выбрано')
    def photos_count(self, obj):
        return obj.selected_photos.count()


@admin.register(Shoot)
class ShootAdmin(admin.ModelAdmin):
    list_display = ('school_class', 'date', 'time', 'status')
    list_filter = ('status', 'date', 'school_class__school')
    search_fields = ('description', 'school_class__name')
    autocomplete_fields = ('school_class',)
    ordering = ('-date',)


# ═══════════════════════════════════════════════════════════════════════════════
#  ГРУППА: АЛЬБОМЫ
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(AlbumTemplate)
class AlbumTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'page_count')
    search_fields = ('name',)
    ordering = ('name',)
    fieldsets = (
        (None, {'fields': ('name', 'page_count')}),
        ('Фоновые изображения', {
            'description': 'Загрузите готовые фоновые изображения для каждого разворота.',
            'fields': ('oblozhka_bg', 'hero_spread_bg', 'grid_spread_bg'),
        }),
        ('HTML-развороты (Jinja2)', {
            'classes': ('collapse',),
            'description': 'Ландшафтные развороты. Оставьте пустыми для встроенных шаблонов. Переменная {{ bg_url }} — путь к фону.',
            'fields': ('oblozhka_spread_template', 'hero_spread_template', 'grid_spread_template'),
        }),
    )


@admin.action(description='📦 Сгенерировать персональные альбомы ZIP')
def generate_personal_albums_zip(modeladmin, request, queryset):
    from django.contrib import messages

    order = queryset.first()
    if not order:
        return

    try:
        generator = AlbumGenerator(order)
        students = order.school_class.students.all().order_by('last_name', 'first_name')

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for student in students:
                pdf_bytes = generator.generate_individual_pdf(student)
                filename = f"Album_{student.last_name}_{student.first_name}.pdf"
                zf.writestr(filename, pdf_bytes)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = (
            f'attachment; filename="Albums_{order.school_class.name}.zip"'
        )
        return response

    except Exception as e:
        modeladmin.message_user(
            request,
            f'Ошибка при генерации: {e}',
            messages.ERROR,
        )


@admin.register(AlbumOrder)
class AlbumOrderAdmin(admin.ModelAdmin):
    list_display = ('school_class', 'template', 'created_at', 'has_pdf')
    list_filter = ('school_class__school', 'template')
    search_fields = ('school_class__name',)
    autocomplete_fields = ('school_class', 'template', 'group_photo_1', 'group_photo_2')
    readonly_fields = ('pdf_file', 'created_at')
    actions = [generate_personal_albums_zip]
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('school_class', 'template')}),
        ('Медиа', {'fields': ('cover_image', 'group_photo_1', 'group_photo_2')}),
        ('Результат', {
            'fields': ('pdf_file', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='PDF', boolean=True)
    def has_pdf(self, obj):
        return bool(obj.pdf_file)
