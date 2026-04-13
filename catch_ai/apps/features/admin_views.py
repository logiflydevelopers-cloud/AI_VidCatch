from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404

from .models import Features
from .serializers import FeatureUpdateSerializer


# ==========================================================
# LIST FEATURES
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAdminUser])
def list_features(request):
    features = Features.objects.all()

    data = [
        {
            "id": f.id,
            "name": f.name,
            "feature_type": f.feature_type,
            "is_multi_mode": f.is_multi_mode,
            "is_active": f.is_active,
        }
        for f in features
    ]

    return Response(data)


# ==========================================================
# GET SINGLE FEATURE
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_feature(request, feature_id):
    f = get_object_or_404(Features, id=feature_id)
    mapping = f.model_mapping or {}

    response = {
        "id": f.id,
        "name": f.name,
        "feature_type": f.feature_type,
        "is_multi_mode": f.is_multi_mode,
        "allowed_models": [m.id for m in f.allowed_models.all()],
        "is_active": f.is_active,
        "is_premium": f.is_premium,
        "credits_config": f.credits_config,
    }

    # =========================
    # MULTI MODE
    # =========================
    if f.is_multi_mode:
        response.update({
            "model_mapping": {
                "fast": mapping.get("fast"),
                "standard": mapping.get("standard"),
                "advanced": mapping.get("advanced"),
                "bw_color": mapping.get("bw_color"),
                "recolor": mapping.get("recolor"),
            },
            "fast_credit_cost": f.fast_credit_cost,
            "standard_credit_cost": f.standard_credit_cost,
            "advanced_credit_cost": f.advanced_credit_cost,
        })

    # =========================
    # SINGLE MODE
    # =========================
    else:
        response.update({
            "model_mapping": {
                "default": mapping.get("default")
            },
            "credit_cost": f.fast_credit_cost  # reuse fast field
        })

    return Response(response)


# ==========================================================
# UPDATE FEATURE
# ==========================================================
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def update_feature(request, feature_id):
    feature = get_object_or_404(Features, id=feature_id)

    data = request.data.copy()

    # =========================
    # MERGE MODEL MAPPING (FIXES OVERWRITE BUG)
    # =========================
    if "model_mapping" in data:
        existing_mapping = feature.model_mapping or {}
        incoming_mapping = data.get("model_mapping") or {}

        existing_mapping.update(incoming_mapping)
        data["model_mapping"] = existing_mapping

    # =========================
    # HANDLE MODE SWITCH
    # =========================
    is_multi_mode = data.get("is_multi_mode", feature.is_multi_mode)

    if not is_multi_mode:
        mapping = data.get("model_mapping") or feature.model_mapping or {}

        # Force only default key
        data["model_mapping"] = {
            "default": mapping.get("default")
        }

        # Remove multi-mode fields
        data.pop("standard_credit_cost", None)
        data.pop("advanced_credit_cost", None)

    else:
        # Remove default if switching to multi
        mapping = data.get("model_mapping") or feature.model_mapping or {}

        mapping.pop("default", None)
        data["model_mapping"] = mapping

    # =========================
    # SERIALIZER SAVE
    # =========================
    serializer = FeatureUpdateSerializer(
        feature,
        data=data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)