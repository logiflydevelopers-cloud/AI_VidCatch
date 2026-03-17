from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.templates.models import Template
from .models import Generation
from .serializers import GenerateSerializer, GenerationSerializer
from .tasks import run_generation


# ==========================================================
# CREATE GENERATION
# ==========================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_generation(request):

    serializer = GenerateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    template_id = serializer.validated_data["template_id"]
    input_data = serializer.validated_data["input_data"]

    # ✅ Only active templates
    template = get_object_or_404(
        Template,
        id=template_id,
        is_active=True
    )

    # ✅ Ensure model exists
    if not template.default_model:
        return Response(
            {"error": "No model configured for this template"},
            status=400
        )

    model = template.default_model

    # ✅ Optional credit system
    if hasattr(request.user, "credits"):
        if request.user.credits < template.credit_cost:
            return Response(
                {"error": "Insufficient credits"},
                status=400
            )

    # ✅ Atomic transaction
    with transaction.atomic():

        generation = Generation.objects.create(
            user=request.user,
            template=template,
            input_data=input_data,
            status="pending",

            # 🔥 snapshot fields (VERY IMPORTANT)
            model_name=model.model_name,
            feature_type=model.feature_type,
            credit_used=model.credit_cost or template.credit_cost
        )

        # send job to celery
        task = run_generation.delay(generation.id)

        generation.task_id = task.id
        generation.save()

        # deduct credits (optional)
        if hasattr(request.user, "credits"):
            request.user.credits -= template.credit_cost
            request.user.save()

    return Response({
        "job_id": generation.job_id,
        "status": "queued",
        "template": template.name
    })


# ==========================================================
# GET GENERATION STATUS
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_generation(request, job_id):

    generation = get_object_or_404(
        Generation.objects.select_related("template"),
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
    ).select_related("template")

    # ✅ optional filters
    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    # ✅ pagination (simple limit)
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