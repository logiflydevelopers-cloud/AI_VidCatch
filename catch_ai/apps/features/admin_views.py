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

    return Response({
        "id": f.id,
        "name": f.name,
        "feature_type": f.feature_type,
        "is_multi_mode": f.is_multi_mode,

        "allowed_models": [m.id for m in f.allowed_models.all()],

        # mapping
        "fast_model": mapping.get("fast"),
        "standard_model": mapping.get("standard"),
        "advanced_model": mapping.get("advanced"),
        "bw_color_model": mapping.get("bw_color"),
        "recolor_model": mapping.get("recolor"),

        "fast_credit_cost": f.fast_credit_cost,
        "standard_credit_cost": f.standard_credit_cost,
        "advanced_credit_cost": f.advanced_credit_cost,

        "is_active": f.is_active,
        "is_premium": f.is_premium,

        "input_schema": f.input_schema,
        "credits_config": f.credits_config,
    })


# ==========================================================
# UPDATE FEATURE
# ==========================================================
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def update_feature(request, feature_id):
    feature = get_object_or_404(Features, id=feature_id)

    serializer = FeatureUpdateSerializer(
        feature,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)