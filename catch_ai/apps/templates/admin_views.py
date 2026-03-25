from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Template
from .serializers import AdminTemplateSerializer
from .permissions import IsAdmin

from apps.services.firebase_storage import upload_file


# ================================
# CREATE TEMPLATE
# ================================
@api_view(["POST"])
@permission_classes([IsAdmin])
def create_template(request):

    # Step 1: Create template (without files first)
    serializer = AdminTemplateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    template = serializer.save()

    # Step 2: Upload Cover Image
    cover_file = request.FILES.get("cover_image")

    if cover_file:
        cover_path = f"templates/{template.id}/cover"
        cover_url = upload_file(cover_file, cover_path)
        template.cover_image = cover_url

    # Step 3: Upload Preview Media (Multiple)
    preview_files = request.FILES.getlist("preview_media")

    preview_urls = []

    if preview_files:
        preview_path = f"templates/{template.id}/previews"

        for file in preview_files:
            url = upload_file(file, preview_path)
            preview_urls.append(url)

    # If your model has JSONField / ArrayField
    if preview_urls:
        template.preview_media = preview_urls

    # Step 4: Save everything
    template.save()

    return Response({
        "message": "Template created successfully",
        "data": AdminTemplateSerializer(template).data
    }, status=status.HTTP_201_CREATED)

# ================================
# UPDATE TEMPLATE
# ================================
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


# ================================
# DELETE TEMPLATE
# ================================
@api_view(["DELETE"])
@permission_classes([IsAdmin])
def delete_template(request, template_id):

    template = get_object_or_404(Template, id=template_id)

    template.delete()

    return Response(
        {"message": "Template deleted"},
        status=status.HTTP_204_NO_CONTENT
    )


# ================================
# UPLOAD TEMPLATE COVER IMAGE
# ================================
@api_view(["POST"])
@permission_classes([IsAdmin])
def upload_template_cover(request, template_id):

    template = get_object_or_404(Template, id=template_id)

    file = request.FILES.get("file")

    if not file:
        return Response(
            {"error": "File is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Firebase path
    path = f"templates/{template_id}/cover"

    url = upload_file(file, path)

    # save url in template
    template.cover_image = url
    template.save()

    return Response({
        "cover_image": url
    })


# ================================
# UPLOAD TEMPLATE PREVIEW MEDIA
# ================================
@api_view(["POST"])
@permission_classes([IsAdmin])
def upload_template_preview(request, template_id):

    template = get_object_or_404(Template, id=template_id)

    file = request.FILES.get("file")

    if not file:
        return Response(
            {"error": "File is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    path = f"templates/{template_id}/previews"

    url = upload_file(file, path)

    return Response({
        "preview_url": url
    })