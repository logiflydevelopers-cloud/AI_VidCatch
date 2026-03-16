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

    template = get_object_or_404(Template, id=template_id)

    generation = Generation.objects.create(
        user=request.user,
        template=template,
        input_data=input_data,
        status="pending"
    )

    # send job to celery
    task = run_generation.delay(generation.id)

    generation.task_id = task.id
    generation.save()

    return Response({
        "job_id": generation.job_id,
        "status": "queued"
    })


# ==========================================================
# GET GENERATION STATUS
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_generation(request, job_id):

    generation = get_object_or_404(
        Generation,
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

    generations = Generation.objects.filter(
        user=request.user
    ).select_related("template").order_by("-created_at")

    serializer = GenerationSerializer(
        generations,
        many=True
    )

    return Response(serializer.data)