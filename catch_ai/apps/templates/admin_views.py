from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Template
from .serializers import AdminTemplateSerializer
from .permissions import IsAdmin


@api_view(["POST"])
@permission_classes([IsAdmin])
def create_template(request):

    serializer = AdminTemplateSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
@permission_classes([IsAdmin])
def update_template(request, template_id):

    template = get_object_or_404(Template, id=template_id)

    serializer = AdminTemplateSerializer(
        template,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAdmin])
def delete_template(request, template_id):

    template = get_object_or_404(Template, id=template_id)

    template.delete()

    return Response(
        {"message": "Template deleted"},
        status=status.HTTP_204_NO_CONTENT
    )