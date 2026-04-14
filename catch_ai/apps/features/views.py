from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Features
from apps.templates.models import AIModel

SPECIAL_FEATURES = ["text_to_video", "image_to_video", "colorize"]

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

# ==========================================================
# HELPER: MERGE BASE + ADDON CREDITS 
# ==========================================================
def get_normalized_credits(feature):

    credits_config = feature.credits_config or {}

    # ============================
    # MULTI MODE
    # ============================
    if feature.is_multi_mode:

        normalized = {
            "fast": {},
            "standard": {},
            "advanced": {}
        }

        for key, modes in credits_config.items():

            if not isinstance(modes, dict):
                continue

            for mode in ["fast", "standard", "advanced"]:
                value = modes.get(mode)

                if value is not None:
                    normalized[mode][key] = value

        return normalized

    # ============================
    # SINGLE MODE
    # ============================
    else:
        return {
            "default": credits_config
        }

def get_feature_settings(feature):

    # ============================
    # MULTI MODE
    # ============================
    if feature.is_multi_mode:
        settings = {}

        qs = feature.settings.all().order_by("display_order")

        for s in qs:
            # Ensure mode exists
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
        data.append({
            "id": f.id,
            "name": f.name,
            "feature_type": f.feature_type,
            "credits": get_normalized_credits(f),
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

    return Response({
        "id": feature.id,
        "name": feature.name,
        "feature_type": feature.feature_type,
        "credits": get_normalized_credits(feature),
        "is_premium": feature.is_premium,
        "models": get_feature_models(feature),

        "default_model": {
            "id": feature.default_model.id,
            "name": feature.default_model.name
        } if feature.default_model and feature.default_model.is_active else None,

        "input_schema": feature.input_schema,
        "settings": get_feature_settings(feature),
    })