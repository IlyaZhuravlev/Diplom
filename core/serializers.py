from rest_framework import serializers
from .models import (
    School, SchoolClass, Student, Photo,
    PhotoSelection, Shoot, AlbumTemplate, AlbumOrder,
    TemplateSpread, TemplateZone,
)


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'


class SchoolClassSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()
    confirmed_count = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = '__all__'

    def get_student_count(self, obj):
        return obj.students.count()

    def get_confirmed_count(self, obj):
        return PhotoSelection.objects.filter(
            student__school_class=obj, is_confirmed=True
        ).count()


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = '__all__'


class PhotoSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoSelection
        fields = '__all__'


class ShootSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shoot
        fields = '__all__'


# ═══════════════════════════════════════════════════════════════════════════════
#  ШАБЛОНЫ: Зоны и развороты
# ═══════════════════════════════════════════════════════════════════════════════

class TemplateZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateZone
        fields = ['id', 'spread', 'zone_type', 'sort_order', 'x', 'y', 'w', 'h']


class TemplateSpreadSerializer(serializers.ModelSerializer):
    zones = TemplateZoneSerializer(many=True, read_only=True)
    zone_count = serializers.SerializerMethodField()
    background_url = serializers.SerializerMethodField()

    class Meta:
        model = TemplateSpread
        fields = [
            'id', 'template', 'spread_order', 'spread_type',
            'background', 'background_url',
            'bg_width', 'bg_height',
            'zones', 'zone_count',
        ]
        read_only_fields = ['bg_width', 'bg_height']

    def get_zone_count(self, obj):
        return obj.zones.count()

    def get_background_url(self, obj):
        if obj.background:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.background.url)
            return obj.background.url
        return None


class AlbumTemplateSerializer(serializers.ModelSerializer):
    spreads = TemplateSpreadSerializer(many=True, read_only=True)
    spread_count = serializers.SerializerMethodField()

    class Meta:
        model = AlbumTemplate
        fields = ['id', 'name', 'spreads', 'spread_count']

    def get_spread_count(self, obj):
        return obj.spreads.count()


# ═══════════════════════════════════════════════════════════════════════════════
#  ЗАКАЗЫ
# ═══════════════════════════════════════════════════════════════════════════════

class AlbumOrderSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='school_class.__str__', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = AlbumOrder
        fields = '__all__'
        read_only_fields = ('pdf_file', 'zip_file', 'status', 'created_at')
