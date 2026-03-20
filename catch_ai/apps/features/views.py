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

    # Special features (fast / standard / advanced)
    if feature.feature_type in SPECIAL_FEATURES and feature.model_mapping:

        data = {}

        for key, model_id in feature.model_mapping.items():
            try:
                model = AIModel.objects.get(id=model_id, is_active=True)

                data[key] = {
                    "id": model.id,
                    "name": model.name
                }

            except AIModel.DoesNotExist:
                data[key] = None

        return data

    # Normal features
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

    # ============================
    # BASE CREDITS (FROM FIELDS)
    # ============================
    if feature.is_multi_mode:
        credits = {
            "fast": feature.fast_credit_cost,
            "standard": feature.standard_credit_cost,
            "advanced": feature.advanced_credit_cost
        }
    else:
        credits = {
            "default": feature.credit_cost
        }

    # ============================
    # ADDONS (FROM JSON)
    # ============================
    if feature.credits_config:
        credits.update(feature.credits_config)

    return credits

def get_feature_settings(feature):

    # ============================
    # MULTI MODE
    # ============================
    if feature.is_multi_mode:
        settings = {
            "fast": {},
            "standard": {},
            "advanced": {}
        }

        qs = feature.settings.all().order_by("display_order")

        for s in qs:
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