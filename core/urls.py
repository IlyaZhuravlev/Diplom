from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchoolViewSet, SchoolClassViewSet, StudentViewSet,
    PhotoViewSet, PhotoSelectionViewSet, ShootViewSet
)

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'classes', SchoolClassViewSet)
router.register(r'students', StudentViewSet)
router.register(r'photos', PhotoViewSet)
router.register(r'selections', PhotoSelectionViewSet)
router.register(r'shoots', ShootViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
