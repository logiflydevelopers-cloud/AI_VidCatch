from rest_framework import serializers
from apps.features.models import Features,  FeatureSetting
from apps.templates.models import AIModel
import copy

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

    model_mapping = serializers.SerializerMethodField()
    default_model = serializers.SerializerMethodField()
    credits = serializers.SerializerMethodField()   # ✅ NEW

    class Meta:
        model = Features
        fields = [
            "id",
            "name",
            "feature_type",
            "credits",    
            "is_premium",
            "model_mapping",
            "default_model",
            "input_schema",
            "default_settings",
        ]

    # -----------------------------
    # 🔥 GET CREDITS (NEW)
    # -----------------------------
    def get_credits(self, obj):

        EXCLUDED_FEATURES = ["text_to_video", "image_to_video"]

        # 👉 Keep existing credits for special features
        if obj.feature_type in EXCLUDED_FEATURES:
            return obj.credits or {}

        # 👉 Default format for normal features
        return {
            "default": {
                "credit_cost": obj.credit_cost or 0
            }
        }

    # -----------------------------
    # GET MODEL MAPPING
    # -----------------------------
    def get_model_mapping(self, obj):

        SPECIAL_FEATURES = ["text_to_video", "image_to_video", "colorize"]

        if obj.feature_type in SPECIAL_FEATURES and obj.model_mapping:

            models_data = {}

            model_ids = set()

            for value in obj.model_mapping.values():

                if isinstance(value, dict):
                    for v in value.values():
                        if v:
                            model_ids.add(str(v))
                else:
                    if value:
                        model_ids.add(str(value))

            models = AIModel.objects.filter(
                id__in=model_ids,
                is_active=True
            )

            model_map = {str(m.id): m for m in models}

            for key, value in obj.model_mapping.items():

                if isinstance(value, dict):
                    models_data[key] = {}

                    for sub_key, model_id in value.items():
                        model = model_map.get(str(model_id))

                        models_data[key][sub_key] = (
                            {
                                "id": model.id,
                                "name": model.name
                            } if model else None
                        )

                else:
                    model = model_map.get(str(value))

                    models_data[key] = (
                        {
                            "id": model.id,
                            "name": model.name
                        } if model else None
                    )

            return models_data

        # -----------------------------
        # NORMAL FEATURES
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


from rest_framework import serializers
from .models import Features, FeatureSetting
from apps.templates.models import AIModel


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
    # 🔥 NEW CREDIT LOGIC (JSON BASED)
    # ==========================================
    def set_default_credit_cost(self, data, instance=None):
        feature_type = data.get("feature_type") or getattr(instance, "feature_type", None)

        credits_config = data.get("credits_config") or getattr(instance, "credits_config", {})

        # 🎨 COLORIZE
        if feature_type == "colorize":
            data["credit_cost"] = credits_config.get("bw_color", 0)

        # 🎬 VIDEO FEATURES (FROM DURATION)
        elif feature_type in ["text_to_video", "image_to_video"]:
            duration = credits_config.get("duration", {})
            fast = duration.get("fast", {})

            data["credit_cost"] = min(fast.values()) if fast else 0

        return data

    # ==========================================
    # VALIDATION
    # ==========================================
    def validate(self, data):

        instance = getattr(self, "instance", None)

        allowed_models = data.get("allowed_models") or instance.allowed_models.all()
        allowed_ids = [str(m.id) for m in allowed_models]

        feature_type = data.get("feature_type") or instance.feature_type
        is_multi_mode = data.get("is_multi_mode", instance.is_multi_mode)

        existing_mapping = instance.model_mapping or {}

        # COLORIZE
        if feature_type == "colorize" and (
            "bw_color_model" in data or "recolor_model" in data
        ):
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

        # MULTI MODE
        elif is_multi_mode and any(
            k in data for k in ["fast_model", "standard_model", "advanced_model"]
        ):
            updated_mapping = existing_mapping.copy()

            for group_key, group_value in existing_mapping.items():

                if not isinstance(group_value, dict):
                    continue

                updated_mapping[group_key] = group_value.copy()

                if data.get("fast_model"):
                    updated_mapping[group_key]["fast"] = str(data["fast_model"].id)

                if data.get("standard_model"):
                    updated_mapping[group_key]["standard"] = str(data["standard_model"].id)

                if data.get("advanced_model"):
                    updated_mapping[group_key]["advanced"] = str(data["advanced_model"].id)

            data["model_mapping"] = updated_mapping

        else:
            data["model_mapping"] = existing_mapping

        data = self.set_default_credit_cost(data, instance)

        return data

    # ==========================================
    # 🔥 SYNC FEATURE SETTINGS
    # ==========================================
    def sync_feature_settings(self, instance):
        config = instance.credits_config or {}

        for key, modes in config.items():

            if not isinstance(modes, dict):
                continue

            for mode, options in modes.items():

                # BOOLEAN CASE (audio)
                if isinstance(options, bool):
                    option_keys = [True, False]

                # SELECT CASE (duration, resolution)
                elif isinstance(options, dict):
                    option_keys = list(options.keys())

                else:
                    continue

                qs = FeatureSetting.objects.filter(
                    feature_id=instance.id,
                    mode=mode,
                    key=key
                )

                obj = qs.first()

                if obj:
                    obj.options = option_keys
                    obj.default_value = option_keys[0] if option_keys else None
                    obj.save()

                    if qs.count() > 1:
                        qs.exclude(id=obj.id).delete()

                else:
                    FeatureSetting.objects.create(
                        feature_id=instance.id,
                        mode=mode,
                        key=key,
                        type="select",
                        options=option_keys,
                        default_value=option_keys[0] if option_keys else None,
                        is_required=True,
                        display_order=0,
                    )

    # ==========================================
    # 🔥 UPDATE
    # ==========================================
    def update(self, instance, validated_data):
        model_mapping = validated_data.pop("model_mapping", None)
        allowed_models = validated_data.pop("allowed_models", None)

        # 🔥 IMPORTANT: handle JSON separately
        credits_config = validated_data.pop("credits_config", None)

        validated_data.pop("fast_model", None)
        validated_data.pop("standard_model", None)
        validated_data.pop("advanced_model", None)
        validated_data.pop("bw_color_model", None)
        validated_data.pop("recolor_model", None)

        # =========================
        # NORMAL FIELDS UPDATE
        # =========================
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # =========================
        # 🔥 CRITICAL FIX (JSON FULL REPLACE)
        # =========================
        if credits_config is not None:
            instance.credits_config = copy.deepcopy(credits_config)

        # =========================
        # MODEL MAPPING
        # =========================
        if model_mapping is not None:
            instance.model_mapping = model_mapping

        # =========================
        # CREDIT COST
        # =========================
        if "credit_cost" in validated_data:
            instance.credit_cost = validated_data["credit_cost"]

        instance.save()

        # 🔥 SYNC SETTINGS AFTER SAVE
        self.sync_feature_settings(instance)

        # =========================
        # MANY-TO-MANY
        # =========================
        if allowed_models is not None:
            instance.allowed_models.set(allowed_models)

        return instance