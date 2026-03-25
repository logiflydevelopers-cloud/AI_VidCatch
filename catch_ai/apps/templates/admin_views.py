from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Template, AIModel
from .serializers import AdminTemplateSerializer, AIModelSerializer
from .permissions import IsAdmin
from django.db import transaction
import json


from apps.services.firebase_storage import upload_file


# ================================
# CREATE TEMPLATE
# ================================
@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAdmin])
def create_template(request):

    try:
        data = request.data.copy()

        # ================================
        # REMOVE FILE FIELDS
        # ================================
        data.pop("cover_image", None)
        data.pop("preview_media", None)

        # ================================
        # CONVERT model_name → id 🔥
        # ================================
        allowed_model_names = request.data.getlist("allowed_models")
        default_model_name = request.data.get("default_model")

        if allowed_model_names:
            models_qs = AIModel.objects.filter(
                model_name__in=allowed_model_names,
                is_active=True
            )

            model_map = {m.model_name: m for m in models_qs}

            # check missing
            missing = set(allowed_model_names) - set(model_map.keys())
            if missing:
                return Response({
                    "error": f"Invalid allowed_models: {list(missing)}"
                }, status=400)

            data.setlist(
                "allowed_models",
                [model_map[name].id for name in allowed_model_names]
            )

        if default_model_name:
            try:
                model_obj = AIModel.objects.get(
                    model_name=default_model_name,
                    is_active=True
                )
                data["default_model"] = model_obj.id
            except AIModel.DoesNotExist:
                return Response({
                    "error": f"Invalid default_model: {default_model_name}"
                }, status=400)

        # ================================
        # VALIDATE SERIALIZER
        # ================================
        serializer = AdminTemplateSerializer(data=data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():

            template = serializer.save()

            # ================================
            # UPLOAD COVER IMAGE
            # ================================
            cover_file = request.FILES.get("cover_image")

            if cover_file:
                cover_path = f"templates/{template.id}/cover"
                template.cover_image = upload_file(cover_file, cover_path)

            # ================================
            # UPLOAD PREVIEW MEDIA
            # ================================
            preview_files = request.FILES.getlist("preview_media")

            if preview_files:
                preview_path = f"templates/{template.id}/previews"

                template.preview_media = [
                    upload_file(file, preview_path)
                    for file in preview_files
                ]

            template.save()

        return Response({
            "message": "Template created successfully",
            "data": AdminTemplateSerializer(template).data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================
# UPDATE TEMPLATE
# ================================
@csrf_exempt
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
@csrf_exempt
@api_view(["DELETE"])
@permission_classes([IsAdmin])
def delete_template(request, template_id):

    template = get_object_or_404(Template, id=template_id)

    template.delete()

    return Response(
        {"message": "Template deleted"},
        status=status.HTTP_204_NO_CONTENT
    )


# # ================================
# # UPLOAD TEMPLATE COVER IMAGE
# # ================================
# @api_view(["POST"])
# @permission_classes([IsAdmin])
# def upload_template_cover(request, template_id):

#     template = get_object_or_404(Template, id=template_id)

#     file = request.FILES.get("file")

#     if not file:
#         return Response(
#             {"error": "File is required"},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # Firebase path
#     path = f"templates/{template_id}/cover"

#     url = upload_file(file, path)

#     # save url in template
#     template.cover_image = url
#     template.save()

#     return Response({
#         "cover_image": url
#     })


# # ================================
# # UPLOAD TEMPLATE PREVIEW MEDIA
# # ================================
# @api_view(["POST"])
# @permission_classes([IsAdmin])
# def upload_template_preview(request, template_id):

#     template = get_object_or_404(Template, id=template_id)

#     file = request.FILES.get("file")

#     if not file:
#         return Response(
#             {"error": "File is required"},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     path = f"templates/{template_id}/previews"

#     url = upload_file(file, path)

#     return Response({
#         "preview_url": url
#     })

# ================================
# GET AI MODELS (ADMIN)
# ================================
@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAdmin])
def get_ai_models(request):

    models = AIModel.objects.all().order_by("-created_at")

    serializer = AIModelSerializer(models, many=True)

    return Response({
        "count": models.count(),
        "data": serializer.data
    })

# ================================
# UPDATE AI MODEL
# ================================
@csrf_exempt
@api_view(["PUT", "PATCH"])
@permission_classes([IsAdmin])
def update_ai_model(request, model_id):

    model = get_object_or_404(AIModel, id=model_id)

    serializer = AIModelSerializer(
        model,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "AI Model updated",
            "data": serializer.data
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)