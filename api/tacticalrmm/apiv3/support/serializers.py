from rest_framework import serializers
from .models import SysTray

class SysTraySerializer(serializers.ModelSerializer):
    class Meta:
        model = SysTray
        fields = '__all__'