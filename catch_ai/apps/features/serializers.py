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

            # Clean IDs (handle string/int safely)
            model_ids = [
                int(v) for v in obj.model_mapping.values() if v
            ]

            # Single DB query (optimization)
            models = AIModel.objects.filter(
                id__in=model_ids,
                is_active=True
            )

            model_map = {m.id: m for m in models}

            # Build response
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

    # ==========================================
    # 🔥 CREDIT LOGIC (NEW)
    # ==========================================
    def set_default_credit_cost(self, data, instance=None):
        feature_type = data.get("feature_type") or getattr(instance, "feature_type", None)

        # ----------------------------------
        # 🎨 COLORIZE
        # ----------------------------------
        if feature_type == "colorize":
            credits_config = data.get("credits_config") or getattr(instance, "credits_config", {})
            data["credit_cost"] = credits_config.get("bw_color", 0)

        # ----------------------------------
        # 🎬 VIDEO FEATURES (USE TOP-LEVEL FIELDS)
        # ----------------------------------
        elif feature_type in ["text_to_video", "image_to_video"]:

            # ✅ PRIORITY → fast_credit_cost
            if "fast_credit_cost" in data:
                data["credit_cost"] = data.get("fast_credit_cost") or 0

            elif instance and getattr(instance, "fast_credit_cost", None) is not None:
                data["credit_cost"] = instance.fast_credit_cost

            else:
                data["credit_cost"] = 0

        return data

    # ==========================================
    # 🔥 VALIDATION
    # ==========================================
    def validate(self, data):

        instance = getattr(self, "instance", None)

        allowed_models = data.get("allowed_models") or instance.allowed_models.all()
        allowed_ids = [str(m.id) for m in allowed_models]

        # 👉 ONLY use feature_type if explicitly provided
        feature_type = data.get("feature_type") or instance.feature_type
        is_multi_mode = data.get("is_multi_mode", instance.is_multi_mode)

        existing_mapping = instance.model_mapping or {}

        # ==========================================
        # 🎨 COLORIZE (ONLY if fields provided)
        # ==========================================
        if feature_type == "colorize" and (
            "bw_color_model" in data or "recolor_model" in data
        ):

            bw = data.get("bw_color_model") or AIModel.objects.filter(
                id=existing_mapping.get("bw_color")
            ).first()

            recolor = data.get("recolor_model") or AIModel.objects.filter(
                id=existing_mapping.get("recolor")
            ).first()

            if not (bw and recolor):
                raise serializers.ValidationError("Both bw_color & recolor required")

            for m in [bw, recolor]:
                if str(m.id) not in allowed_ids:
                    raise serializers.ValidationError(f"{m} not in allowed_models")

            data["model_mapping"] = {
                "bw_color": str(bw.id),
                "recolor": str(recolor.id),
            }

        # ==========================================
        # 🎬 MULTI MODE (ONLY if fields provided)
        # ==========================================
        elif is_multi_mode and (
            "fast_model" in data
            or "standard_model" in data
            or "advanced_model" in data
        ):

            fast = data.get("fast_model") or AIModel.objects.filter(
                id=existing_mapping.get("fast")
            ).first()

            standard = data.get("standard_model") or AIModel.objects.filter(
                id=existing_mapping.get("standard")
            ).first()

            advanced = data.get("advanced_model") or AIModel.objects.filter(
                id=existing_mapping.get("advanced")
            ).first()

            if not (fast and standard and advanced):
                raise serializers.ValidationError("All 3 models required in multi mode")

            for m in [fast, standard, advanced]:
                if str(m.id) not in allowed_ids:
                    raise serializers.ValidationError(f"{m} not in allowed_models")

            data["model_mapping"] = {
                "fast": str(fast.id),
                "standard": str(standard.id),
                "advanced": str(advanced.id),
            }

        # ==========================================
        # 🧩 DO NOTHING (PATCH SAFE)
        # ==========================================
        else:
            # 👉 keep existing mapping if not updating
            data["model_mapping"] = existing_mapping

        # ==========================================
        # 💰 CREDIT LOGIC
        # ==========================================
        data = self.set_default_credit_cost(data, instance)

        return data

    # ==========================================
    # 🔥 UPDATE
    # ==========================================
    def update(self, instance, validated_data):
        model_mapping = validated_data.pop("model_mapping", None)
        allowed_models = validated_data.pop("allowed_models", None)

        # remove temp fields
        validated_data.pop("fast_model", None)
        validated_data.pop("standard_model", None)
        validated_data.pop("advanced_model", None)
        validated_data.pop("bw_color_model", None)
        validated_data.pop("recolor_model", None)

        # update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # apply mapping
        if model_mapping is not None:
            instance.model_mapping = model_mapping

        # apply credit_cost
        if "credit_cost" in validated_data:
            instance.credit_cost = validated_data["credit_cost"]

        instance.save()

        # update M2M
        if allowed_models is not None:
            instance.allowed_models.set(allowed_models)

        return instance