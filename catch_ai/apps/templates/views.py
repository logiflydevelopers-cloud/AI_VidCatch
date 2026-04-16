from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Template, GenerationConfig
from .serializers import TemplateSerializer, GenerationConfigSerializer



# ================================
# LIST TEMPLATES
# ================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_templates(request):

    category = request.query_params.get("category")
    feature_type = request.query_params.get("feature_type")

    templates = Template.objects.filter(is_active=True)

    if category:
        templates = templates.filter(category=category)

    if feature_type:
        templates = templates.filter(feature_type=feature_type)

    templates = templates.prefetch_related(
        "allowed_models"
    ).order_by("display_order", "-created_at")

    template_data = TemplateSerializer(templates, many=True).data

    # 👇 ADD AUTO VIDEO CONFIG
    auto_video = GenerationConfig.objects.filter(
        config_type="auto_video"
    )

    auto_video_data = GenerationConfigSerializer(auto_video, many=True).data

    return Response({
        "templates": template_data,
        "auto_video": auto_video_data
    })


# ================================
# GET TEMPLATE DETAILS
# ================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_template(request, template_id):

    template = get_object_or_404(
        Template.objects.prefetch_related("allowed_models"),
        id=template_id,
        is_active=True
    )

    serializer = TemplateSerializer(template)

    return Response(serializer.data)