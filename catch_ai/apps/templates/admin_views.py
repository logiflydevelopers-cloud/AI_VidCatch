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
from django.db.models import Q

from apps.services.firebase_storage import upload_file
from rest_framework.pagination import PageNumberPagination


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
        # CONVERT model_name / name → id 🔥
        # ================================
        allowed_inputs = request.data.getlist("allowed_models")
        default_input = request.data.get("default_model")

        if allowed_inputs:
            models_qs = AIModel.objects.filter(
                is_active=True
            ).filter(
                Q(model_name__in=allowed_inputs) |
                Q(name__in=allowed_inputs)
            )

            # map both model_name & name → object
            model_map = {}
            for m in models_qs:
                model_map[m.model_name] = m
                model_map[m.name] = m

            # check missing
            missing = [m for m in allowed_inputs if m not in model_map]
            if missing:
                return Response({
                    "error": f"Invalid allowed_models: {missing}"
                }, status=400)

            data.setlist(
                "allowed_models",
                [model_map[m].id for m in allowed_inputs]
            )

        # ================================
        # DEFAULT MODEL
        # ================================
        if default_input:
            model_obj = AIModel.objects.filter(
                Q(model_name=default_input) | Q(name=default_input),
                is_active=True
            ).first()

            if not model_obj:
                return Response({
                    "error": f"Invalid default_model: {default_input}"
                }, status=400)

            data["default_model"] = model_obj.id

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
                template.cover_image = upload_file(
                    cover_file,
                    f"templates/{template.id}/cover"
                )

            # ================================
            # UPLOAD PREVIEW MEDIA
            # ================================
            preview_files = request.FILES.getlist("preview_media")

            if preview_files:
                template.preview_media = [
                    upload_file(file, f"templates/{template.id}/previews")
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

# ================================
# PAGINATION CLASS
# ================================
class TemplatePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ================================
# GET ALL TEMPLATES
# ================================
@api_view(["GET"])
def get_templates(request):

    try:
        queryset = Template.objects.all().order_by("-created_at")

        # ================================
        # FILTERS (OPTIONAL)
        # ================================
        category = request.GET.get("category")
        feature_type = request.GET.get("feature_type")
        is_active = request.GET.get("is_active")

        if category:
            queryset = queryset.filter(category=category)

        if feature_type:
            queryset = queryset.filter(feature_type=feature_type)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # ================================
        # OPTIMIZATION
        # ================================
        queryset = queryset.select_related("default_model").prefetch_related("allowed_models")

        # ================================
        # PAGINATION
        # ================================
        paginator = TemplatePagination()
        paginated_qs = paginator.paginate_queryset(queryset, request)

        serializer = AdminTemplateSerializer(paginated_qs, many=True)

        return paginator.get_paginated_response({
            "count": queryset.count(),
            "results": serializer.data
        })

    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)