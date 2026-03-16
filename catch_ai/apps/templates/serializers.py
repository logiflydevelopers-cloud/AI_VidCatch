from rest_framework import serializers
from .models import Template, AIModel


# USER SERIALIZER
class TemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Template
        fields = [
            "id",
            "name",
            "cover_image",
            "credit_cost",
            "feature_type",
            "prompt_template",
            "input_schema",
            "default_settings",
            "category"
        ]


# ADMIN SERIALIZER
class AdminTemplateSerializer(serializers.ModelSerializer):

    allowed_models = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(),
        many=True
    )

    class Meta:
        model = Template
        fields = "__all__"