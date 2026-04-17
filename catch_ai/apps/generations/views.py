from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from apps.templates.models import Template, AIModel
from apps.features.models import Features
from .models import Generation
from .serializers import GenerateSerializer, GenerationSerializer
from .tasks import run_generation

from django.db.models import Q

from .pagination import GenerationPagination   
import random

SPECIAL_FEATURES = ["text_to_video", "image_to_video", "colorize"]


# ==========================================================
# HELPERS
# ==========================================================
def validate_feature_settings(feature, mode, user_settings):
    db_settings = feature.settings.filter(mode=mode)

    allowed = {}
    required_keys = set()

    for s in db_settings:
        allowed[s.key] = s.options
        if s.is_required:
            required_keys.add(s.key)

    user_settings = user_settings or {}

    # -------------------------
    # Check required fields
    # -------------------------
    for key in required_keys:
        if key not in user_settings:
            raise ValidationError(f"Missing required setting: {key}")

    # -------------------------
    # Validate values
    # -------------------------
    for key, value in user_settings.items():

        if key not in allowed:
            raise ValidationError(f"Invalid setting: {key}")

        if allowed[key] and value not in allowed[key]:
            raise ValidationError(
                f"Invalid value '{value}' for {key}. Allowed: {allowed[key]}"
            )

    return user_settings


def apply_default_settings(feature, mode, user_settings):
    db_settings = feature.settings.filter(mode=mode)

    final = user_settings.copy() if user_settings else {}

    for s in db_settings:
        if s.key not in final:
            if s.default_value is not None:
                final[s.key] = s.default_value
            elif s.options:
                final[s.key] = s.options[0]

    return final


# ==========================================================
# MAIN API
# ==========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_generation(request):

    try:
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        template = data.get("template_obj")
        feature = data.get("feature_obj")
        input_data = data["input_data"]
        user_settings = data.get("settings")
        quality = data.get("quality")

        model = None
        feature_key = None
        credit_cost = 1
        model_provider = None
        settings = {}

        # ==========================================================
        # TEMPLATE FLOW
        # ==========================================================
        if template:

            if not template.default_model:
                return Response({"error": "No model configured for this template"}, status=400)

            model = template.default_model
            feature_key = model.feature_type
            credit_cost = template.credit_cost
            model_provider = getattr(model, "provider", None)

            settings = template.default_settings 

        # ==========================================================
        # FEATURE FLOW
        # ==========================================================
        elif feature:

            feature_key = feature.feature_type

            if feature.feature_type in SPECIAL_FEATURES:

                if not quality:
                    return Response({"error": "quality is required"}, status=400)

                if not feature.model_mapping:
                    return Response({"error": "Model mapping not configured"}, status=400)

                valid_modes = set()

                if feature.feature_type == "image_to_video":
                    for group in feature.model_mapping.values():
                        if isinstance(group, dict):
                            valid_modes.update(group.keys())
                else:
                    valid_modes = set(feature.model_mapping.keys())

                if quality not in valid_modes:
                    return Response({"error": f"Invalid quality: {quality}. Allowed: {list(valid_modes)}"}, status=400)

                model_id = None

                if feature.feature_type == "image_to_video":
                    for group in feature.model_mapping.values():
                        if isinstance(group, dict) and quality in group:
                            model_id = group.get(quality)
                            break
                else:
                    model_id = feature.model_mapping.get(quality)

                if not model_id:
                    return Response({"error": f"No model configured for {quality}"}, status=400)

                try:
                    model = AIModel.objects.get(id=model_id, is_active=True)
                except AIModel.DoesNotExist:
                    return Response({"error": "Mapped model not found or inactive"}, status=400)

                if model not in feature.allowed_models.all():
                    return Response({"error": "Model not allowed for this feature"}, status=400)

                if feature.credits_config and quality in feature.credits_config:
                    credit_cost = feature.credits_config.get(quality, 1)
                else:
                    credit_cost = feature.credit_cost or 1

                try:
                    settings = validate_feature_settings(feature, quality, user_settings)
                    settings = apply_default_settings(feature, quality, settings)
                except ValidationError as e:
                    return Response({"error": str(e)}, status=400)

            else:

                if quality:
                    return Response({"error": "Quality not allowed for this feature"}, status=400)

                if not feature.default_model:
                    return Response({"error": "No model configured for this feature"}, status=400)

                model = feature.default_model
                credit_cost = feature.credit_cost or 1
                model_provider = getattr(model, "provider", None)

                settings = user_settings or {}

        else:
            return Response({"error": "Invalid request"}, status=400)

        # ==========================================================
        # 🔥 FIX 1: CLEAN INPUT DATA
        # ==========================================================
        final_input_data = input_data.copy()

        # 🚨 CRITICAL: convert prompt list → string
        if "prompt" in final_input_data:
            prompt = final_input_data["prompt"]

            if isinstance(prompt, list):
                prompt = random.choice(prompt)

            if not isinstance(prompt, str):
                return Response(
                    {"error": f"Invalid prompt type: {type(prompt)}"},
                    status=400
                )

            final_input_data["prompt"] = prompt.strip()

        # ==========================================================
        # 🔥 FIX 2: BLOCK FRONTEND PROMPT FOR AUTO VIDEO
        # ==========================================================
        if request.data.get("source_type") == "auto_video":
            final_input_data.pop("prompt", None)

        # ==========================================================
        # PROMPT INJECTION (TEMPLATE)
        # ==========================================================
        if template and template.prompt_template:
            try:
                final_prompt = template.prompt_template.format(**input_data)
            except KeyError as e:
                return Response(
                    {"error": f"Missing input for prompt variable: {str(e)}"},
                    status=400
                )

            final_input_data["prompt"] = final_prompt

        # ==========================================================
        # PAYLOAD
        # ==========================================================
        payload = {
            "feature": feature_key,
            "model": model.model_name,
            "inputs": final_input_data,
        }

        if settings:
            payload["settings"] = settings

        # ==========================================================
        # CREATE GENERATION
        # ==========================================================
        with transaction.atomic():

            generation = Generation.objects.create(
                user=request.user,
                template=template,
                feature=feature,
                input_data=final_input_data,
                status="pending",

                model_name=model.model_name,
                feature_type=feature_key,
                model_provider=model_provider,
                credit_used=credit_cost,

                request_payload=payload,

                input_summary=(template.name if template else feature.name)
            )

            model.track_usage()

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

        return Response({"error": str(e)}, status=500)
    

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
# USER GENERATION HISTORY (PAGINATED)
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_generations(request):

    queryset = (
        Generation.objects
        .filter(user=request.user)
        .select_related("template", "feature")
        .order_by("-created_at")
    )

    # ==========================
    # FILTERS
    # ==========================
    status = request.GET.get("status")
    source_type = request.GET.get("type")
    result_type = request.GET.get("result_type")

    if status:
        queryset = queryset.filter(status=status)

    if source_type:
        queryset = queryset.filter(source_type=source_type)

    if result_type:
        queryset = queryset.filter(result_type=result_type)

    # ==========================
    # SEARCH
    # ==========================
    search = request.GET.get("search")
    if search:
        queryset = queryset.filter(
            Q(input_summary__icontains=search) |
            Q(template__name__icontains=search) |
            Q(feature__name__icontains=search)
        )

    # ==========================
    # PAGINATION (DRF)
    # ==========================
    paginator = GenerationPagination()
    page = paginator.paginate_queryset(queryset, request)

    serializer = GenerationSerializer(page, many=True)

    return paginator.get_paginated_response(serializer.data)