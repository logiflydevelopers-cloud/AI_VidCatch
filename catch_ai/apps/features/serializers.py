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
            "input_schema"
            "default_settings",
        ]

    # -----------------------------
    # GET MODELS
    # -----------------------------
    def get_models(self, obj):

        SPECIAL_FEATURES = ["text_to_video", "image_to_video", "colorize"]

        # -----------------------------
        # Special features → mapped models
        # -----------------------------
        if obj.feature_type in SPECIAL_FEATURES and obj.model_mapping:

            models_data = {}

            # 🔥 Clean IDs (handle string/int safely)
            model_ids = [
                int(v) for v in obj.model_mapping.values() if v
            ]

            # 🔥 Single DB query (optimization)
            models = AIModel.objects.filter(
                id__in=model_ids,
                is_active=True
            )

            model_map = {m.id: m for m in models}

            # 🔥 Build response
            for key, model_id in obj.model_mapping.items():

                try:
                    model_id = int(model_id)
                except (TypeError, ValueError):
                    models_data[key] = None
                    continue

                model = model_map.get(model_id)

                if model:
                    models_data[key] = {
                        "id": model.id,
                        "name": model.name
                    }
                else:
                    models_data[key] = None  # fallback

            return models_data

        # -----------------------------
        # Normal features → list
        # -----------------------------
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


class FeatureUpdateSerializer(serializers.ModelSerializer):

    # extra fields (same as form)
    fast_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(), required=False, allow_null=True
    )
    standard_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(), required=False, allow_null=True
    )
    advanced_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(), required=False, allow_null=True
    )

    bw_color_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(), required=False, allow_null=True
    )
    recolor_model = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Features
        exclude = ("model_mapping",)

    def validate(self, data):
        request = self.context.get("request")

        allowed_models = data.get("allowed_models", [])
        allowed_ids = [str(m.id) for m in allowed_models]

        feature_type = data.get("feature_type", self.instance.feature_type)
        is_multi_mode = data.get("is_multi_mode", self.instance.is_multi_mode)

        # ----------------------------------
        # MULTI MODE
        # ----------------------------------
        if is_multi_mode:
            fast = data.get("fast_model")
            standard = data.get("standard_model")
            advanced = data.get("advanced_model")

            if not (fast and standard and advanced):
                raise serializers.ValidationError("All 3 models required in multi mode")

            # validate allowed_models
            for m in [fast, standard, advanced]:
                if str(m.id) not in allowed_ids:
                    raise serializers.ValidationError(f"{m} not in allowed_models")

            data["model_mapping"] = {
                "fast": str(fast.id),
                "standard": str(standard.id),
                "advanced": str(advanced.id),
            }

        # ----------------------------------
        # COLORIZE MODE
        # ----------------------------------
        elif feature_type == "colorize":
            bw = data.get("bw_color_model")
            recolor = data.get("recolor_model")

            if not (bw and recolor):
                raise serializers.ValidationError("Both bw_color & recolor required")

            for m in [bw, recolor]:
                if str(m.id) not in allowed_ids:
                    raise serializers.ValidationError(f"{m} not in allowed_models")

            data["model_mapping"] = {
                "bw_color": str(bw.id),
                "recolor": str(recolor.id),
            }

        # ----------------------------------
        # NORMAL MODE
        # ----------------------------------
        else:
            data["model_mapping"] = None

        return data

    def update(self, instance, validated_data):
        model_mapping = validated_data.pop("model_mapping", None)

        # remove extra fields
        validated_data.pop("fast_model", None)
        validated_data.pop("standard_model", None)
        validated_data.pop("advanced_model", None)
        validated_data.pop("bw_color_model", None)
        validated_data.pop("recolor_model", None)

        # update main fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # set mapping
        instance.model_mapping = model_mapping

        instance.save()
        return instance