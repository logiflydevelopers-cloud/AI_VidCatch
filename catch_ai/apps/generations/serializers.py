from rest_framework import serializers
from .models import Generation
from apps.templates.models import Template
from apps.features.models import Features


class GenerateSerializer(serializers.Serializer):

    template_id = serializers.CharField(required=False)
    feature_id = serializers.CharField(required=False)

    input_data = serializers.JSONField()

    def validate(self, data):

        template_id = data.get("template_id")
        feature_id = data.get("feature_id")
        input_data = data.get("input_data", {})

        # =====================================
        # VALIDATE SOURCE (template OR feature)
        # =====================================
        if not template_id and not feature_id:
            raise serializers.ValidationError(
                "Either template_id or feature_id is required"
            )

        if template_id and feature_id:
            raise serializers.ValidationError(
                "Only one of template_id or feature_id is allowed"
            )

        # =====================================
        # TEMPLATE FLOW
        # =====================================
        if template_id:
            try:
                template = Template.objects.get(id=template_id, is_active=True)
            except Template.DoesNotExist:
                raise serializers.ValidationError("Template not found")

            schema = template.input_schema or {}

        # =====================================
        # FEATURE FLOW
        # =====================================
        else:
            try:
                feature = Features.objects.get(id=feature_id, is_active=True)
            except Features.DoesNotExist:
                raise serializers.ValidationError("Feature not found")

            schema = feature.input_schema or {}

        # =====================================
        # VALIDATE INPUTS AGAINST SCHEMA
        # =====================================
        fields = schema.get("fields", [])

        for field in fields:
            name = field.get("name")
            required = field.get("required", False)

            if required and name not in input_data:
                raise serializers.ValidationError(f"{name} is required")

        return data


class GenerationSerializer(serializers.ModelSerializer):

    template_name = serializers.SerializerMethodField()
    feature_name = serializers.SerializerMethodField()

    job_id = serializers.CharField(read_only=True)
    processing_time = serializers.SerializerMethodField()

    class Meta:
        model = Generation

        fields = [
            "job_id",
            "template",
            "template_name",
            "feature",
            "feature_name",
            "status",
            "result_url",
            "result_type",
            "error_message",
            "model_name",
            "feature_type",
            "input_data",
            "created_at",
            "completed_at",
            "processing_time",
        ]

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None

    def get_feature_name(self, obj):
        return obj.feature.name if obj.feature else None

    def get_processing_time(self, obj):
        return obj.processing_time