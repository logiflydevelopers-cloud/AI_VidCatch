from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Features


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
            "credit_cost": f.credit_cost,
            "is_premium": f.is_premium,
            "input_schema": f.input_schema,
            "default_settings": f.default_settings,
            "template_id": f.template.id if f.template else None,
        })

    return Response(data)


# ==========================================================
# SINGLE FEATURE
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feature(request, feature_id):

    feature = get_object_or_404(Features, id=feature_id)

    return Response({
        "id": feature.id,
        "name": feature.name,
        "feature_type": feature.feature_type,
        "credit_cost": feature.credit_cost,
        "template_id": feature.template.id if feature.template else None,
        "input_schema": feature.input_schema,
        "default_settings": feature.default_settings,
    })