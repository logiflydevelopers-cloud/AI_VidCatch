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

    # ✅ Make these optional because we upload separately
    cover_image = serializers.CharField(required=False, allow_null=True)
    preview_media = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    class Meta:
        model = Template
        fields = "__all__"

    def validate(self, data):

        allowed_models = data.get("allowed_models")
        default_model = data.get("default_model")
        feature_type = data.get("feature_type")

        # ✅ default_model must be inside allowed_models
        if default_model:
            if allowed_models and default_model not in allowed_models:
                raise serializers.ValidationError(
                    "default_model must be in allowed_models"
                )

            # ✅ feature_type match
            if default_model.feature_type != feature_type:
                raise serializers.ValidationError(
                    "Model feature_type must match template feature_type"
                )

        return data

    def create(self, validated_data):
        """
        Handle M2M properly
        """
        allowed_models = validated_data.pop("allowed_models", [])
        
        template = Template.objects.create(**validated_data)

        if allowed_models:
            template.allowed_models.set(allowed_models)

        return template

    def update(self, instance, validated_data):
        """
        Handle update + M2M
        """
        allowed_models = validated_data.pop("allowed_models", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if allowed_models is not None:
            instance.allowed_models.set(allowed_models)

        instance.save()
        return instance