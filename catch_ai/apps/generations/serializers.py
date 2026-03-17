from rest_framework import serializers
from .models import Generation
from apps.templates.models import Template


class GenerateSerializer(serializers.Serializer):

    template_id = serializers.CharField()
    input_data = serializers.JSONField()

    def validate(self, data):

        template_id = data.get("template_id")
        input_data = data.get("input_data")

        try:
            template = Template.objects.get(id=template_id)
        except Template.DoesNotExist:
            raise serializers.ValidationError("Template not found")

        schema = template.input_schema or {}
        fields = schema.get("fields", [])

        for field in fields:
            name = field.get("name")
            required = field.get("required", False)

            if required and name not in input_data:
                raise serializers.ValidationError(f"{name} is required")

        return data


class GenerationSerializer(serializers.ModelSerializer):

    template_name = serializers.CharField(source="template.name", read_only=True)
    job_id = serializers.CharField(read_only=True)
    processing_time = serializers.SerializerMethodField()

    class Meta:
        model = Generation

        fields = [
            "job_id",
            "template",
            "template_name",
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

    def get_processing_time(self, obj):
        return obj.processing_time