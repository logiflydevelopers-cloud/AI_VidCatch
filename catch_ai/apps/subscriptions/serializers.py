from rest_framework import serializers
from .models import Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "credits_per_month",
            "price",
            "daily_limit",
            "features",
            "validity_days",
            "is_active",
        ]

        