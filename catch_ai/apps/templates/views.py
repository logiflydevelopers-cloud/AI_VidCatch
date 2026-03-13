from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Template
from .serializers import TemplateSerializer


@api_view(["GET"])
def list_templates(request):

    templates = Template.objects.filter(is_active=True)

    serializer = TemplateSerializer(templates, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def get_template(request, template_id):

    template = Template.objects.filter(
        id=template_id,
        is_active=True
    ).first()

    if not template:
        return Response({"error": "Template not found"}, status=404)

    serializer = TemplateSerializer(template)

    return Response(serializer.data)