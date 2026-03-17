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
            "preview_media",
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
        queryset=AIModel.objects.filter(is_active=True),
        many=True
    )

    default_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Template
        fields = "__all__"

    def validate(self, data):

        allowed_models = data.get("allowed_models")
        default_model = data.get("default_model")
        feature_type = data.get("feature_type")

        # ✅ default_model must be in allowed_models
        if default_model:
            if allowed_models and default_model not in allowed_models:
                raise serializers.ValidationError(
                    "default_model must be in allowed_models"
                )

            # ✅ feature must match
            if default_model.feature_type != feature_type:
                raise serializers.ValidationError(
                    "Model feature_type must match template feature_type"
                )

        return data