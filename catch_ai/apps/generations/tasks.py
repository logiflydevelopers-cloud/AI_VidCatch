import requests

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Generation
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
        # SAVE SNAPSHOT
        # ============================
        generation.model_name = model.model_name
        generation.feature_type = model.feature_type
        generation.save()

        # ============================
        # BUILD PAYLOAD
        # ============================
        payload = {
            "feature": model.feature_type,
            "model": model.model_name,
            "inputs": generation.input_data
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

        # ============================
        # DETECT RESULT TYPE
        # ============================
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

        # retry if possible
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:

            generation.status = "failed"
            generation.error_message = str(exc)
            generation.completed_at = timezone.now()
            generation.save()