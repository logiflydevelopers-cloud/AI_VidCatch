from rest_framework import serializers
from .models import Template, AIModel

# AI MODEL SERIALIZER
class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = [
            "id",
            "name",
            "feature_type",
            "provider",
            "credit_cost",
            "is_active"
        ]



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
            "category",
            "label"
        ]


# ADMIN SERIALIZER
class AdminTemplateSerializer(serializers.ModelSerializer):

    allowed_models = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.filter(is_active=True),
        many=True,
        required=False
    )

    default_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    input_schema = serializers.JSONField(required=False)
    default_settings = serializers.JSONField(required=False)

    cover_image = serializers.CharField(required=False, allow_null=True)
    preview_media = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Template
        fields = "__all__"
        extra_kwargs = {
            "cover_image": {"required": False},
            "preview_media": {"required": False},
            "default_settings": {"required": False},
            "prompt_template": {"required": False},
        }

    # ============================
    # VALIDATION
    # ============================
    def validate(self, data):

        allowed_models = data.get("allowed_models", [])
        default_model = data.get("default_model")
        feature_type = data.get("feature_type")

        if default_model:
            if allowed_models and default_model not in allowed_models:
                raise serializers.ValidationError({
                    "default_model": "Must be included in allowed_models"
                })

            if feature_type and default_model.feature_type != feature_type:
                raise serializers.ValidationError({
                    "default_model": "Model feature_type must match template feature_type"
                })

        return data

    # ============================
    # CREATE
    # ============================
    def create(self, validated_data):

        allowed_models = validated_data.pop("allowed_models", [])

        template = Template.objects.create(**validated_data)

        if allowed_models:
            template.allowed_models.set(allowed_models)

        return template

    # ============================
    # UPDATE
    # ============================
    def update(self, instance, validated_data):

        allowed_models = validated_data.pop("allowed_models", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if allowed_models is not None:
            instance.allowed_models.set(allowed_models)

        instance.save()
        return instance