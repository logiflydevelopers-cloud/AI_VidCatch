from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Features
from apps.templates.models import AIModel

SPECIAL_FEATURES = ["text_to_video", "image_to_video"]

# ==========================================================
# HELPER: GET MODELS
# ==========================================================
def get_feature_models(feature):

    # =========================================
    # SPECIAL CASE: IMAGE TO VIDEO
    # =========================================
    if feature.feature_type == "image_to_video" and feature.model_mapping:

        data = {}
        model_ids = []

        # collect all model ids (nested)
        for value in feature.model_mapping.values():
            if isinstance(value, dict):
                model_ids.extend([v for v in value.values() if v])

        models = AIModel.objects.filter(
            id__in=model_ids,
            is_active=True
        )

        model_map = {m.id: m for m in models}

        # build nested response
        for group_key, modes in feature.model_mapping.items():

            data[group_key] = {}

            if isinstance(modes, dict):
                for mode, model_id in modes.items():

                    model = model_map.get(model_id)

                    data[group_key][mode] = {
                        "id": model.id,
                        "name": model.name
                    } if model else None

        return data

    # =========================================
    # EXISTING LOGIC
    # =========================================
    if feature.feature_type in SPECIAL_FEATURES and feature.model_mapping:

        data = {}

        model_ids = [
            v for v in feature.model_mapping.values() if v
        ]

        models = AIModel.objects.filter(
            id__in=model_ids,
            is_active=True
        )

        model_map = {m.id: m for m in models}

        for key, model_id in feature.model_mapping.items():

            if not model_id:
                data[key] = None
                continue

            model = model_map.get(model_id)

            if model:
                data[key] = {
                    "id": model.id,
                    "name": model.name
                }
            else:
                data[key] = None

        return data

    # =========================================
    # NORMAL FEATURES
    # =========================================
    return [
        {
            "id": m.id,
            "name": m.name
        }
        for m in feature.allowed_models.filter(is_active=True)
    ]

def clean_audio_config(audio):
    if not isinstance(audio, dict):
        return audio

    # remove repeated config nesting
    config = audio.get("config", {})

    while isinstance(config, dict) and "config" in config:
        config = config["config"]

    return {
        "enabled": audio.get("enabled", True),
        "config": config
    }

def transform_credits_structure(credits):

    if not isinstance(credits, dict):
        return {}

    result = {}

    # =========================
    # AUDIO (FLAT)
    # =========================
    audio_config = {}

    for mode in ["fast", "standard", "advanced"]:
        mode_data = credits.get(mode, {})

        audio = mode_data.get("audio", {})
        if not isinstance(audio, dict):
            continue

        if audio.get("enabled"):
            config = audio.get("config", {})

            # unwrap nested config if any
            while isinstance(config, dict) and "config" in config:
                config = config["config"]

            for k, v in config.items():
                audio_config[k] = v

    if audio_config:
        result["audio"] = audio_config

    # =========================
    # DURATION
    # =========================
    duration = {}

    for mode in ["fast", "standard", "advanced"]:
        mode_data = credits.get(mode, {})

        if "duration" in mode_data:
            duration[mode] = mode_data["duration"]

    if duration:
        result["duration"] = duration

    # =========================
    # RESOLUTION
    # =========================
    resolution = {}

    for mode in ["fast", "standard", "advanced"]:
        mode_data = credits.get(mode, {})

        if "resolution" in mode_data:
            resolution[mode] = mode_data["resolution"]

    if resolution:
        result["resolution"] = resolution

    return result

# ==========================================================
# HELPER: MERGE BASE + ADDON CREDITS 
# ==========================================================
def get_normalized_credits(feature):

    feature_type = (feature.feature_type or "").strip().lower()
    credits_config = feature.credits_config or {}

    MULTI_MODE_FEATURES = ["text_to_video", "image_to_video"]

    # ======================================================
    # MULTI-MODE FEATURES (TEXT TO VIDEO, IMAGE TO VIDEO)
    # ======================================================
    if feature_type in MULTI_MODE_FEATURES and feature.is_multi_mode:

        normalized = {
            "fast": {},
            "standard": {},
            "advanced": {}
        }

        for key, value in credits_config.items():

            # ============================
            # CASE 1: MODE-BASED
            # ============================
            if isinstance(value, dict) and any(
                k in ["fast", "standard", "advanced"] for k in value.keys()
            ):
                for mode in ["fast", "standard", "advanced"]:
                    if mode in value:
                        normalized[mode][key] = value[mode]

            # ============================
            # CASE 2: GLOBAL (audio etc.)
            # ============================
            else:
                for mode in ["fast", "standard", "advanced"]:

                    if key == "audio":
                        normalized[mode][key] = clean_audio_config(value)
                    else:
                        normalized[mode][key] = value

        return normalized

    # ======================================================
    # SINGLE / NORMAL FEATURES (COLORIZE ETC.)
    # ======================================================
    # 🔥 PRIORITY: credits_config
    if credits_config:
        return {
            "default": credits_config
        }

    # ======================================================
    # FALLBACK (SIMPLE CREDIT)
    # ======================================================
    return {
        "default": {
            "credit_cost": feature.credit_cost or 0
        }
    }

def get_feature_settings(feature):

    EXCLUDED_KEYS = ["config"]
    EXCLUDED_MODES = ["config"]   # ✅ NEW

    # ============================
    # MULTI MODE
    # ============================
    if feature.is_multi_mode:
        settings = {}

        qs = feature.settings.all().order_by("display_order")

        for s in qs:

            key = (s.key or "").strip().lower()
            mode = (s.mode or "").strip().lower()

            # ❌ SKIP CONFIG MODE
            if mode in EXCLUDED_MODES:
                continue

            # ❌ SKIP CONFIG KEY (extra safety)
            if key in EXCLUDED_KEYS:
                continue

            if s.mode not in settings:
                settings[s.mode] = {}

            settings[s.mode][s.key] = s.options

        return settings

    # ============================
    # NORMAL FEATURE
    # ============================
    settings = {}

    qs = feature.settings.all().order_by("display_order")

    for s in qs:

        key = (s.key or "").strip().lower()

        if key in EXCLUDED_KEYS:
            continue

        settings[s.key] = s.options

    return settings

# ==========================================================
# LIST FEATURES
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_features(request):

    queryset = Features.objects.filter(
        is_active=True
    ).order_by("display_order")

    data = []

    for f in queryset:

        normalized = get_normalized_credits(f)

        if f.feature_type in SPECIAL_FEATURES:
            credits = transform_credits_structure(normalized)
        else:
            credits = normalized

        data.append({
            "id": f.id,
            "name": f.name,
            "feature_type": f.feature_type,
            "credits": credits,
            "is_premium": f.is_premium,
            "models": get_feature_models(f),

            "default_model": {
                "id": f.default_model.id,
                "name": f.default_model.name
            } if f.default_model and f.default_model.is_active else None,

            "input_schema": f.input_schema,
            "settings": get_feature_settings(f),
        })

    return Response(data)

# ==========================================================
# SINGLE FEATURE
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feature(request, feature_id):

    feature = get_object_or_404(Features, id=feature_id, is_active=True)

    normalized = get_normalized_credits(feature)

    if feature.feature_type in SPECIAL_FEATURES:
        credits = transform_credits_structure(normalized)
    else:
        credits = normalized

    return Response({
        "id": feature.id,
        "name": feature.name,
        "feature_type": feature.feature_type,
        "credits": credits,
        "is_premium": feature.is_premium,
        "models": get_feature_models(feature),

        "default_model": {
            "id": feature.default_model.id,
            "name": feature.default_model.name
        } if feature.default_model and feature.default_model.is_active else None,

        "input_schema": feature.input_schema,
        "settings": get_feature_settings(feature),
    })