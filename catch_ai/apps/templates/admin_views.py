from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from .models import Template
from .serializers import TemplateSerializer
from .permissions import IsAdmin


@api_view(["POST"])
@permission_classes([IsAdmin])
def create_template(request):

    serializer = TemplateSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)


@api_view(["PUT"])
@permission_classes([IsAdmin])
def update_template(request, template_id):

    template = Template.objects.get(id=template_id)

    serializer = TemplateSerializer(
        template,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAdmin])
def delete_template(request, template_id):

    template = Template.objects.get(id=template_id)

    template.delete()

    return Response({"message": "Template deleted"})