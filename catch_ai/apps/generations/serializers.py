from rest_framework import serializers
from .models import Generation
from apps.templates.models import Template
from apps.features.models import Features



from rest_framework import serializers
from apps.templates.models import Template
from apps.features.models import Features


class GenerateSerializer(serializers.Serializer):

    template_id = serializers.CharField(required=False)
    feature_id = serializers.CharField(required=False)

    # optional (future use)
    model_id = serializers.CharField(required=False)

    input_data = serializers.JSONField()
    settings = serializers.JSONField(required=False)

    # ✅ FIX: dynamic quality (NO hardcoding)
    quality = serializers.CharField(required=False)

    def validate(self, data):

        template_id = data.get("template_id")
        feature_id = data.get("feature_id")
        input_data = data.get("input_data", {})
        settings = data.get("settings")
        quality = data.get("quality")

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
        # VALIDATE TYPES
        # =====================================
        if not isinstance(input_data, dict):
            raise serializers.ValidationError("input_data must be an object")

        if settings and not isinstance(settings, dict):
            raise serializers.ValidationError("settings must be an object")

        # =====================================
        # FETCH SOURCE
        # =====================================
        template = None
        feature = None

        if template_id:
            try:
                template = Template.objects.get(id=template_id, is_active=True)
            except Template.DoesNotExist:
                raise serializers.ValidationError("Template not found")

            schema = template.input_schema or {}

        else:
            try:
                feature = Features.objects.get(id=feature_id, is_active=True)
            except Features.DoesNotExist:
                raise serializers.ValidationError("Feature not found")

            schema = feature.input_schema or {}

        # attach to validated_data
        data["template_obj"] = template
        data["feature_obj"] = feature

        # =====================================
        # 🔥 DYNAMIC QUALITY VALIDATION
        # =====================================
        if feature:

            # If feature has model_mapping → dynamic modes
            if feature.model_mapping:

                if not quality:
                    raise serializers.ValidationError({
                        "quality": "This field is required"
                    })

                if quality not in feature.model_mapping:
                    raise serializers.ValidationError({
                        "quality": f"{quality} is not a valid choice"
                    })

            else:
                # Normal feature → quality not allowed
                if quality:
                    raise serializers.ValidationError({
                        "quality": "Not allowed for this feature"
                    })

        # =====================================
        # INPUT SCHEMA VALIDATION
        # =====================================
        fields = schema.get("fields", [])
        clean_input = {}

        for field in fields:
            name = field.get("name")
            required = field.get("required", False)
            field_type = field.get("type")

            value = input_data.get(name)

            # required validation
            if required and name not in input_data:
                raise serializers.ValidationError(f"{name} is required")

            if value is None:
                continue

            # ============================
            # TYPE VALIDATION
            # ============================
            if field_type == "number":
                if not isinstance(value, (int, float)):
                    raise serializers.ValidationError(f"{name} must be a number")

            elif field_type == "string":
                if not isinstance(value, str):
                    raise serializers.ValidationError(f"{name} must be a string")

            elif field_type == "image":
                if not isinstance(value, str):
                    raise serializers.ValidationError(f"{name} must be an image URL")

            # ============================
            # LIMIT VALIDATION
            # ============================
            min_val = field.get("min")
            max_val = field.get("max")

            if isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    raise serializers.ValidationError(f"{name} must be >= {min_val}")

                if max_val is not None and value > max_val:
                    raise serializers.ValidationError(f"{name} must be <= {max_val}")

            clean_input[name] = value

        # If no schema → allow all inputs
        if not fields:
            clean_input = input_data

        data["input_data"] = clean_input

        # =====================================
        # SETTINGS VALIDATION
        # =====================================
        if settings:
            data["settings"] = settings

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