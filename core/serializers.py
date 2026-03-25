from rest_framework import serializers
from .models import School, SchoolClass, Student, Photo, PhotoSelection, Shoot

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'

class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = '__all__'

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
