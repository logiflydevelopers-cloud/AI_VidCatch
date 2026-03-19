from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.templates.models import Template
from apps.features.models import Features
from .models import Generation
from .serializers import GenerateSerializer, GenerationSerializer
from .tasks import run_generation


# ==========================================================
# CREATE GENERATION (TEMPLATE + FEATURE)
# ==========================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_generation(request):

    try:
        # ============================
        # VALIDATE INPUT
        # ============================
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        template = data.get("template_obj")
        feature = data.get("feature_obj")
        input_data = data["input_data"]
        user_settings = data.get("settings")

        model = None
        feature_key = None
        credit_cost = 1
        model_provider = None
        settings = None

        # ============================
        # RESOLVE SOURCE
        # ============================
        if template:
            if not template.default_model:
                return Response(
                    {"error": "No model configured for this template"},
                    status=400
                )

            model = template.default_model
            feature_key = model.feature_type
            credit_cost = model.credit_cost or template.credit_cost
            model_provider = getattr(model, "provider", None)

        elif feature:
            if not feature.default_model:
                return Response(
                    {"error": "No model configured for this feature"},
                    status=400
                )

            model = feature.default_model
            feature_key = feature.feature_type
            credit_cost = model.credit_cost or feature.credit_cost
            model_provider = getattr(model, "provider", None)

        else:
            return Response({"error": "Invalid request"}, status=400)

        # ============================
        # RESOLVE SETTINGS
        # Priority:
        # user > template > feature
        # ============================
        if user_settings:
            settings = user_settings

        elif template and getattr(template, "default_settings", None):
            settings = template.default_settings

        elif feature and getattr(feature, "default_settings", None):
            settings = feature.default_settings

        # ============================
        # BUILD PAYLOAD
        # ============================
        payload = {
            "feature": feature_key,
            "model": model.model_name,
            "inputs": input_data
        }

        if settings:
            payload["settings"] = settings

        # ============================
        # CREATE GENERATION
        # ============================
        with transaction.atomic():

            generation = Generation.objects.create(
                user=request.user,

                template=template,
                feature=feature,

                input_data=input_data,
                status="pending",

                # snapshot
                model_name=model.model_name,
                feature_type=feature_key,
                model_provider=model_provider,
                credit_used=credit_cost,

                # debug
                request_payload=payload,

                # UX
                input_summary=(
                    template.name if template else feature.name
                )
            )

            # ============================
            # SEND TO CELERY
            # ============================
            task = run_generation.delay(generation.id, payload)

            generation.task_id = task.id
            generation.save()

        return Response({
            "job_id": generation.job_id,
            "status": "queued",
            "source": "template" if template else "feature",
            "name": template.name if template else feature.name
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return Response(
            {"error": str(e)},
            status=500
        )


# ==========================================================
# GET GENERATION STATUS
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_generation(request, job_id):

    generation = get_object_or_404(
        Generation.objects.select_related("template", "feature"),
        job_id=job_id,
        user=request.user
    )

    serializer = GenerationSerializer(generation)

    return Response(serializer.data)


# ==========================================================
# USER GENERATION HISTORY
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_generations(request):

    queryset = Generation.objects.filter(
        user=request.user
    ).select_related("template", "feature")

    # optional filters
    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    # pagination
    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))

    generations = queryset.order_by("-created_at")[offset:offset + limit]

    serializer = GenerationSerializer(
        generations,
        many=True
    )

    return Response({
        "count": queryset.count(),
        "results": serializer.data
    })