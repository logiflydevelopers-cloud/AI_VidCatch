from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Template
from .serializers import TemplateSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_templates(request):

    templates = Template.objects.filter(
        is_active=True
    ).order_by("-created_at")

    serializer = TemplateSerializer(templates, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_template(request, template_id):

    template = get_object_or_404(
        Template,
        id=template_id,
        is_active=True
    )

    serializer = TemplateSerializer(template)

    return Response(serializer.data)