from rest_framework import serializers
from apps.features.models import Features
from apps.templates.models import AIModel


# ==========================================================
# AI MODEL SERIALIZER (Reusable)
# ==========================================================
class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = ["id", "name"]


# ==========================================================
# FEATURE SERIALIZER
# ==========================================================
class FeatureSerializer(serializers.ModelSerializer):

    models = serializers.SerializerMethodField()
    default_model = serializers.SerializerMethodField()

    class Meta:
        model = Features
        fields = [
            "id",
            "name",
            "feature_type",
            "credit_cost",
            "is_premium",
            "models",
            "default_model",
            "input_schema",
            "default_settings",
        ]

    # -----------------------------
    # GET MODELS
    # -----------------------------
    def get_models(self, obj):

        SPECIAL_FEATURES = ["text_to_video", "image_to_video"]

        # Special features → return mapped models
        if obj.feature_type in SPECIAL_FEATURES and obj.model_mapping:

            models_data = {}

            for key, model_id in obj.model_mapping.items():
                try:
                    model = AIModel.objects.get(id=model_id, is_active=True)

                    models_data[key] = {
                        "id": model.id,
                        "name": model.name
                    }

                except AIModel.DoesNotExist:
                    models_data[key] = None  # safety fallback

            return models_data

        # Normal features → return list
        return [
            {
                "id": model.id,
                "name": model.name
            }
            for model in obj.allowed_models.filter(is_active=True)
        ]

    # -----------------------------
    # GET DEFAULT MODEL
    # -----------------------------
    def get_default_model(self, obj):

        if obj.default_model and obj.default_model.is_active:
            return {
                "id": obj.default_model.id,
                "name": obj.default_model.name
            }

        return None