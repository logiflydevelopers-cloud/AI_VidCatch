from rest_framework import serializers
from .models import Generation
from apps.templates.models import Template
from apps.features.models import Features


class GenerateSerializer(serializers.Serializer):

    template_id = serializers.IntegerField(required=False)
    feature_id = serializers.IntegerField(required=False)

    # future-ready (optional)
    model_id = serializers.IntegerField(required=False)

    input_data = serializers.JSONField()

    def validate(self, data):

        template_id = data.get("template_id")
        feature_id = data.get("feature_id")
        input_data = data.get("input_data", {})

        # =====================================
        # VALIDATE SOURCE
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
        # VALIDATE INPUT DATA TYPE
        # =====================================
        if not isinstance(input_data, dict):
            raise serializers.ValidationError("input_data must be an object")

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
        # VALIDATE AGAINST SCHEMA
        # =====================================
        fields = schema.get("fields", [])

        field_names = [f.get("name") for f in fields]

        clean_input = {}

        for field in fields:
            name = field.get("name")
            required = field.get("required", False)

            if required and name not in input_data:
                raise serializers.ValidationError(f"{name} is required")

            if name in input_data:
                clean_input[name] = input_data[name]

        # If no schema → allow all inputs (important flexibility)
        if not fields:
            clean_input = input_data

        # =====================================
        # SAVE CLEANED DATA
        # =====================================
        data["input_data"] = clean_input

        return data


class GenerationSerializer(serializers.ModelSerializer):

    template_name = serializers.SerializerMethodField()
    feature_name = serializers.SerializerMethodField()

    processing_time = serializers.SerializerMethodField()

    class Meta:
        model = Generation

        fields = [
            "job_id",

            # source
            "source_type",
            "template",
            "template_name",
            "feature",
            "feature_name",

            # status
            "status",
            "error_message",

            # result
            "result_url",
            "result_type",

            # metadata
            "model_name",
            "feature_type",
            "model_provider",
            "credit_used",

            # input
            "input_data",

            # optional debug
            "request_payload",
            "response_payload",

            # timestamps
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