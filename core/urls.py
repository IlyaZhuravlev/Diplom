from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchoolViewSet, SchoolClassViewSet, StudentViewSet,
    PhotoViewSet, PhotoSelectionViewSet, ShootViewSet,
    AlbumTemplateViewSet, AlbumOrderViewSet,
    TemplateSpreadViewSet, TemplateZoneViewSet,
)

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'classes', SchoolClassViewSet)
router.register(r'students', StudentViewSet)
router.register(r'photos', PhotoViewSet)
router.register(r'selections', PhotoSelectionViewSet)
router.register(r'shoots', ShootViewSet)
router.register(r'album-templates', AlbumTemplateViewSet)
router.register(r'album-orders', AlbumOrderViewSet)
router.register(r'spreads', TemplateSpreadViewSet)
router.register(r'zones', TemplateZoneViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
