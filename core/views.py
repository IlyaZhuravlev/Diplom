from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import School, SchoolClass, Student, Photo, PhotoSelection, Shoot
from .serializers import (
    SchoolSerializer, SchoolClassSerializer, StudentSerializer,
    PhotoSerializer, PhotoSelectionSerializer, ShootSerializer
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
        if student_id == 'null':
            queryset = queryset.filter(student__isnull=True)
            if class_id:
                queryset = queryset.filter(school_class_id=class_id)
        elif student_id:
            queryset = queryset.filter(Q(student_id=student_id) | Q(student__isnull=True))
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
