
from rest_framework import serializers
from .models import PlanSlide


class PlanSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanSlide
        fields = "__all__"