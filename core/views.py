import os
import traceback

from django.conf import settings
from django.http import HttpResponse, FileResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q

from .models import (
    School, SchoolClass, Student, Photo,
    PhotoSelection, Shoot, AlbumTemplate, AlbumOrder,
    TemplateSpread, TemplateZone,
)
from .serializers import (
    SchoolSerializer, SchoolClassSerializer, StudentSerializer,
    PhotoSerializer, PhotoSelectionSerializer, ShootSerializer,
    AlbumTemplateSerializer, AlbumOrderSerializer,
    TemplateSpreadSerializer, TemplateZoneSerializer,
)


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer


class SchoolClassViewSet(viewsets.ModelViewSet):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassSerializer


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        queryset = Student.objects.all()
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(school_class_id=class_id)
        return queryset


class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer

    def get_queryset(self):
        queryset = Photo.objects.all()
        student_id = self.request.query_params.get('student_id')
        class_id = self.request.query_params.get('class_id')
        photo_type = self.request.query_params.get('photo_type')

        if student_id == 'null':
            queryset = queryset.filter(student__isnull=True)
            if class_id:
                queryset = queryset.filter(school_class_id=class_id)
        elif student_id:
            queryset = queryset.filter(Q(student_id=student_id) | Q(student__isnull=True))

        if class_id and student_id != 'null':
            queryset = queryset.filter(school_class_id=class_id)

        if photo_type:
            queryset = queryset.filter(photo_type=photo_type)

        return queryset


class PhotoSelectionViewSet(viewsets.ModelViewSet):
    queryset = PhotoSelection.objects.all()
    serializer_class = PhotoSelectionSerializer

    @action(detail=False, methods=['post'])
    def confirm(self, request):
        student_id = request.data.get('student_id')
        photo_ids = request.data.get('photo_ids', [])

        if not student_id:
            return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(id=student_id)
            selection, created = PhotoSelection.objects.get_or_create(student=student)
            selection.selected_photos.set(photo_ids)
            selection.is_confirmed = True
            selection.save()
            return Response({'status': 'confirmed'})
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


class ShootViewSet(viewsets.ModelViewSet):
    queryset = Shoot.objects.all()
    serializer_class = ShootSerializer


# ═══════════════════════════════════════════════════════════════════════════════
#  ШАБЛОНЫ: Развороты и зоны
# ═══════════════════════════════════════════════════════════════════════════════

class AlbumTemplateViewSet(viewsets.ModelViewSet):
    queryset = AlbumTemplate.objects.all()
    serializer_class = AlbumTemplateSerializer


class TemplateSpreadViewSet(viewsets.ModelViewSet):
    queryset = TemplateSpread.objects.all()
    serializer_class = TemplateSpreadSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = TemplateSpread.objects.all()
        template_id = self.request.query_params.get('template_id')
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs.order_by('spread_order')

    def perform_create(self, serializer):
        """После создания разворота — автодетект зон."""
        spread = serializer.save()
        from .zone_detector import detect_and_create_zones
        count = detect_and_create_zones(spread)
        # Сохраняем количество найденных зон в контекст для ответа
        spread._detected_zone_count = count

    def perform_update(self, serializer):
        """При обновлении фона — перезапуск автодетекта."""
        old_instance = self.get_object()
        old_bg_name = old_instance.background.name if old_instance.background else None
        spread = serializer.save()
        new_bg_name = spread.background.name if spread.background else None
        # Перезапуск детекта только если фон изменился
        if new_bg_name and new_bg_name != old_bg_name:
            from .zone_detector import detect_and_create_zones
            detect_and_create_zones(spread)

    @action(detail=True, methods=['post'])
    def redetect(self, request, pk=None):
        """Перезапуск автодетекта зелёных зон."""
        spread = self.get_object()
        from .zone_detector import detect_and_create_zones
        try:
            count = detect_and_create_zones(spread)
            # Возвращаем обновлённый объект с зонами
            serializer = self.get_serializer(spread)
            return Response({
                'status': 'ok',
                'zones_detected': count,
                'spread': serializer.data,
            })
        except Exception as e:
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TemplateZoneViewSet(viewsets.ModelViewSet):
    queryset = TemplateZone.objects.all()
    serializer_class = TemplateZoneSerializer

    def get_queryset(self):
        qs = TemplateZone.objects.all()
        spread_id = self.request.query_params.get('spread_id')
        if spread_id:
            qs = qs.filter(spread_id=spread_id)
        return qs.order_by('sort_order')

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Массовое обновление зон (из фронтенд-редактора).
        Принимает JSON:
        {
            "spread_id": 123,
            "zones": [
                {"id": 1, "x": 100, "y": 200, "w": 300, "h": 400, "zone_type": "student", "sort_order": 0},
                {"id": null, "x": 500, "y": 600, "w": 300, "h": 400, "zone_type": "group", "sort_order": 1},
                ...
            ]
        }
        Зоны с id=null создаются как новые, остальные обновляются.
        Зоны, не попавшие в список, удаляются.
        """
        spread_id = request.data.get('spread_id')
        zones_data = request.data.get('zones', [])

        if not spread_id:
            return Response(
                {'error': 'spread_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            spread = TemplateSpread.objects.get(id=spread_id)
        except TemplateSpread.DoesNotExist:
            return Response(
                {'error': 'Spread not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Собираем ID обновляемых зон
        incoming_ids = set()
        to_create = []
        to_update = []

        for z in zones_data:
            zone_id = z.get('id')
            if zone_id:
                incoming_ids.add(zone_id)
                to_update.append(z)
            else:
                to_create.append(z)

        # Удаляем зоны, не попавшие в новый список
        spread.zones.exclude(id__in=incoming_ids).delete()

        # Обновляем существующие зоны
        for z in to_update:
            TemplateZone.objects.filter(id=z['id'], spread=spread).update(
                x=z['x'], y=z['y'], w=z['w'], h=z['h'],
                zone_type=z.get('zone_type', 'group'),
                sort_order=z.get('sort_order', 0),
            )

        # Создаём новые зоны
        new_zones = []
        for z in to_create:
            new_zones.append(TemplateZone(
                spread=spread,
                x=z['x'], y=z['y'], w=z['w'], h=z['h'],
                zone_type=z.get('zone_type', 'group'),
                sort_order=z.get('sort_order', 0),
            ))
        TemplateZone.objects.bulk_create(new_zones)

        # Возвращаем обновлённые данные
        updated_zones = TemplateZone.objects.filter(spread=spread).order_by('sort_order')
        serializer = TemplateZoneSerializer(updated_zones, many=True)
        return Response({
            'status': 'ok',
            'zones': serializer.data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
#  ЗАКАЗЫ АЛЬБОМОВ
# ═══════════════════════════════════════════════════════════════════════════════

class AlbumOrderViewSet(viewsets.ModelViewSet):
    queryset = AlbumOrder.objects.all()
    serializer_class = AlbumOrderSerializer

    def get_queryset(self):
        qs = AlbumOrder.objects.all()
        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(school_class_id=class_id)
        return qs

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """
        Запускает генерацию ZIP с персональными альбомами.
        POST /api/album-orders/{id}/generate/
        """
        from .pdf_generator import AlbumGenerator
        from django.core.files.base import ContentFile

        order = self.get_object()

        try:
            order.status = 'generating'
            order.save(update_fields=['status'])

            generator = AlbumGenerator(order)
            zip_bytes = generator.generate_class_zip()

            # Сохраняем ZIP в поле модели
            filename = f"Albums_{order.school_class.name}_{order.id}.zip"
            order.zip_file.save(filename, ContentFile(zip_bytes), save=False)
            order.status = 'ready'
            order.save(update_fields=['status', 'zip_file'])

            return Response({
                'status': 'ready',
                'zip_url': order.zip_file.url,
                'message': f'Альбомы сгенерированы! Файл: {filename}',
            })

        except Exception as e:
            order.status = 'error'
            order.save(update_fields=['status'])
            traceback.print_exc()
            return Response(
                {'error': str(e), 'status': 'error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'])
    def download_zip(self, request, pk=None):
        """Скачивание готового ZIP."""
        order = self.get_object()
        if not order.zip_file:
            return Response(
                {'error': 'ZIP ещё не сгенерирован'},
                status=status.HTTP_404_NOT_FOUND,
            )

        file_path = order.zip_file.path
        if not os.path.exists(file_path):
            return Response(
                {'error': 'Файл не найден на диске'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(file_path),
        )

    @action(detail=True, methods=['get'])
    def class_status(self, request, pk=None):
        """Статус готовности класса к генерации альбомов."""
        order = self.get_object()
        sc = order.school_class
        students = sc.students.all().order_by('last_name', 'first_name')

        student_statuses = []
        for student in students:
            is_confirmed = PhotoSelection.objects.filter(
                student=student, is_confirmed=True
            ).exists()
            has_portrait = Photo.objects.filter(
                student=student, photo_type='portrait'
            ).exists()
            student_statuses.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'is_confirmed': is_confirmed,
                'has_portrait': has_portrait,
            })

        group_photos = Photo.objects.filter(
            school_class=sc, photo_type='group'
        )
        group_photo_data = []
        for p in group_photos:
            group_photo_data.append({
                'id': p.id,
                'url': p.image.url if p.image else '',
            })

        return Response({
            'class_name': str(sc),
            'total_students': students.count(),
            'confirmed_count': sum(1 for s in student_statuses if s['is_confirmed']),
            'students': student_statuses,
            'group_photos': group_photo_data,
            'order_status': order.status,
            'zip_url': order.zip_file.url if order.zip_file else None,
        })
