from rest_framework import serializers
from .models import Generation
from apps.templates.models import Template


# ============================================
# GENERATION CREATE SERIALIZER
# ============================================

class GenerateSerializer(serializers.Serializer):

    template_id = serializers.CharField()
    input_data = serializers.JSONField()

    def validate_template_id(self, value):

        if not Template.objects.filter(id=value).exists():
            raise serializers.ValidationError("Template not found")

        return value


# ============================================
# GENERATION RESPONSE SERIALIZER
# ============================================

class GenerationSerializer(serializers.ModelSerializer):

    template_name = serializers.CharField(source="template.name", read_only=True)
    job_id = serializers.CharField(read_only=True)

    class Meta:
        model = Generation

        fields = [
            "job_id",
            "template",
            "template_name",
            "status",
            "result_url",
            "error_message",
            "created_at",
            "completed_at",
        ]