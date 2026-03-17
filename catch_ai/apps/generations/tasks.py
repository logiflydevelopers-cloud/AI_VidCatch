import requests

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Generation
from apps.templates.models import Template
from apps.services.firebase_storage import upload_generated_image


FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id):

    generation = Generation.objects.select_related(
        "template__default_model"
    ).get(id=generation_id)

    try:
        # ============================
        # SET PROCESSING
        # ============================
        generation.status = "processing"
        generation.started_at = timezone.now()
        generation.save()

        template = generation.template
        model = template.default_model

        if not model:
            raise Exception("No default model configured")

        # ============================
        # SNAPSHOT (for audit/debug)
        # ============================
        generation.model_name = model.model_name
        generation.feature_type = model.feature_type
        generation.save()

        # ============================
        # VALIDATE INPUTS (schema based)
        # ============================
        user_inputs = generation.input_data or {}
        schema_fields = template.input_schema.get("fields", [])

        allowed_fields = [f["name"] for f in schema_fields]

        # Required validation
        for field in schema_fields:
            if field.get("required") and field["name"] not in user_inputs:
                raise Exception(f"{field['name']} is required")

        # Remove unwanted fields
        clean_inputs = {
            k: v for k, v in user_inputs.items() if k in allowed_fields
        }

        # ============================
        # INJECT PROMPT FROM TEMPLATE
        # ============================
        if template.prompt_template:
            clean_inputs["prompt"] = template.prompt_template

        # ============================
        # BUILD FASTAPI PAYLOAD
        # ============================
        payload = {
            "feature": model.feature_type,
            "model": model.model_name,
            "inputs": clean_inputs
        }

        # ============================
        # CALL FASTAPI
        # ============================
        response = requests.post(
            FASTAPI_GENERATE_URL,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        ai_result_url = data.get("result_url")

        if not ai_result_url:
            raise Exception("AI result URL missing")

        result_type = data.get("type", "image")

        # ============================
        # UPLOAD TO FIREBASE
        # ============================
        firebase_url = upload_generated_image(
            ai_result_url,
            generation.user.id
        )

        # ============================
        # SAVE SUCCESS
        # ============================
        generation.result_url = firebase_url
        generation.result_type = result_type
        generation.status = "completed"
        generation.completed_at = timezone.now()
        generation.save()

        return firebase_url

    except Exception as exc:

        generation.retry_count += 1
        generation.save()

        # Retry logic
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:

            generation.status = "failed"
            generation.error_message = str(exc)
            generation.completed_at = timezone.now()
            generation.save()