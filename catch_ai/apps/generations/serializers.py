from rest_framework import serializers
from .models import Generation
from apps.templates.models import Template, GenerationConfig
from apps.features.models import Features


# ==========================================================
# HELPER: GET VALID MODES
# ==========================================================
def get_valid_modes(feature):
    if not feature.model_mapping:
        return set()

    # nested (image_to_video)
    if feature.feature_type == "image_to_video":
        modes = set()
        for group in feature.model_mapping.values():
            if isinstance(group, dict):
                modes.update(group.keys())
        return modes

    # flat
    return set(feature.model_mapping.keys())


# ==========================================================
# HELPER: GET DEFAULT MODE
# ==========================================================
def get_default_mode(feature):
    if not feature.model_mapping:
        return None

    if feature.feature_type == "image_to_video":
        first_group = next(iter(feature.model_mapping.values()), {})
        return next(iter(first_group.keys()), "fast")

    return next(iter(feature.model_mapping.keys()), "fast")


# ==========================================================
# MAIN SERIALIZER
# ==========================================================
class GenerateSerializer(serializers.Serializer):

    source_type = serializers.CharField(required=False)

    template_id = serializers.CharField(required=False)
    feature_id = serializers.CharField(required=False)

    model_id = serializers.CharField(required=False)

    input_data = serializers.JSONField()
    settings = serializers.JSONField(required=False)

    quality = serializers.CharField(required=False)

    def validate(self, data):

        template_id = data.get("template_id")
        feature_id = data.get("feature_id")
        input_data = data.get("input_data", {})
        settings = data.get("settings")
        quality = data.get("quality")
        source_type = data.get("source_type")

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

        data["template_obj"] = template
        data["feature_obj"] = feature

        # =====================================
        # AUTO CONFIG
        # =====================================
        if source_type == "auto_video" and feature:

            config = GenerationConfig.objects.filter(
                config_type="auto_video",
                is_active=True
            ).first()

            if not config:
                raise serializers.ValidationError("Auto video config not found")

            db_settings = config.default_settings or {}

            user_settings = settings or {}

            # Merge (user overrides default)
            merged_settings = {**db_settings, **user_settings}

            data["settings"] = merged_settings

            prompt = config.prompt_template

            if not prompt:
                raise serializers.ValidationError("Prompt template missing")

            data["input_data"]["prompt"] = prompt

        # =====================================
        # QUALITY LOGIC
        # =====================================
        if feature:

            if feature.model_mapping:

                valid_modes = get_valid_modes(feature)

                if source_type == "auto_video":
                    data["quality"] = get_default_mode(feature)

                else:
                    if not quality:
                        raise serializers.ValidationError({
                            "quality": "This field is required"
                        })

                    if quality not in valid_modes:
                        raise serializers.ValidationError({
                            "quality": f"{quality} is not valid. Allowed: {list(valid_modes)}"
                        })

            else:
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

            if required and name not in input_data:
                raise serializers.ValidationError(f"{name} is required")

            if value is None:
                continue

            if field_type == "number":
                if not isinstance(value, (int, float)):
                    raise serializers.ValidationError(f"{name} must be a number")

            elif field_type == "string":
                if not isinstance(value, str):
                    raise serializers.ValidationError(f"{name} must be a string")

            elif field_type == "image":
                if not isinstance(value, str):
                    raise serializers.ValidationError(f"{name} must be an image URL")

            min_val = field.get("min")
            max_val = field.get("max")

            if isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    raise serializers.ValidationError(f"{name} must be >= {min_val}")

                if max_val is not None and value > max_val:
                    raise serializers.ValidationError(f"{name} must be <= {max_val}")

            clean_input[name] = value

        if not fields:
            clean_input = input_data

        data["input_data"] = clean_input

        return data


# ==========================================================
# GENERATION SERIALIZER
# ==========================================================
class GenerationSerializer(serializers.ModelSerializer):

    template_name = serializers.SerializerMethodField()
    feature_name = serializers.SerializerMethodField()
    processing_time = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "job_id",
            "source_type",
            "template",
            "template_name",
            "feature",
            "feature_name",
            "status",
            "error_message",
            "result_url",
            "result_type",
            "model_name",
            "feature_type",
            "model_provider",
            "credit_used",
            "input_data",
            "request_payload",
            "response_payload",
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


# ==========================================================
# HISTORY SERIALIZER
# ==========================================================
class GenerationHistorySerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "job_id",
            "name",
            "source_type",
            "status",
            "result_url",
            "result_type",
            "credit_used",
            "created_at",
            "completed_at",
            "processing_time",
            "thumbnail",
        ]

    def get_name(self, obj):
        if obj.input_summary:
            return obj.input_summary
        if obj.template:
            return obj.template.name
        if obj.feature:
            return obj.feature.name
        return "Untitled"

    def get_thumbnail(self, obj):
        if obj.result_type == "image":
            return obj.result_url
        return None