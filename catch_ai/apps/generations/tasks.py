import requests
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Generation
from apps.services.firebase_storage import upload_generated_image

FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id):

    print("\n========== START GENERATION TASK ==========")
    print("GENERATION ID:", generation_id)

    generation = Generation.objects.select_related(
        "template__default_model"
    ).get(id=generation_id)

    try:
        # ============================
        # SET PROCESSING
        # ============================
        print("STEP 1: Setting processing state")
        generation.status = "processing"
        generation.started_at = timezone.now()
        generation.save()

        template = generation.template
        model = template.default_model

        print("TEMPLATE ID:", template.id)
        print("MODEL OBJECT:", model)

        if not model:
            raise Exception("No default model configured")

        print("FEATURE:", model.feature_type)
        print("MODEL NAME:", model.model_name)

        # ============================
        # SNAPSHOT
        # ============================
        generation.model_name = model.model_name
        generation.feature_type = model.feature_type
        generation.save()

        # ============================
        # VALIDATE INPUTS
        # ============================
        print("STEP 2: Validating inputs")

        user_inputs = generation.input_data or {}
        schema_fields = template.input_schema.get("fields", [])

        print("USER INPUTS:", user_inputs)
        print("SCHEMA:", schema_fields)

        allowed_fields = [f["name"] for f in schema_fields]

        for field in schema_fields:
            if field.get("required") and field["name"] not in user_inputs:
                raise Exception(f"{field['name']} is required")

        clean_inputs = {
            k: v for k, v in user_inputs.items() if k in allowed_fields
        }

        print("CLEAN INPUTS:", clean_inputs)

        if not clean_inputs:
            raise Exception("Inputs became empty after filtering")

        # ============================
        # PROMPT
        # ============================
        if template.prompt_template:
            clean_inputs["prompt"] = template.prompt_template

        # ============================
        # BUILD PAYLOAD
        # ============================
        print("STEP 3: Building payload")

        payload = {
            "feature": model.feature_type,
            "model": model.model_name,
            "inputs": clean_inputs
        }

        print("PAYLOAD:", payload)
        print("FASTAPI URL:", FASTAPI_GENERATE_URL)

        # ============================
        # CALL FASTAPI
        # ============================
        print("STEP 4: Calling FastAPI...")

        response = requests.post(
            FASTAPI_GENERATE_URL,
            json=payload,
            timeout=300
        )

        print("FASTAPI STATUS:", response.status_code)
        print("FASTAPI RESPONSE TEXT:", response.text)

        response.raise_for_status()

        data = response.json()

        print("PARSED RESPONSE:", data)

        ai_result_url = data.get("result_url") or data.get("result")

        print("AI RESULT URL:", ai_result_url)

        if not ai_result_url:
            raise Exception("AI result URL missing")

        result_type = data.get("type", "image")

        # ============================
        # UPLOAD TO FIREBASE
        # ============================
        print("STEP 5: Uploading to Firebase")

        firebase_url = upload_generated_image(
            ai_result_url,
            generation.user.id
        )

        print("FIREBASE URL:", firebase_url)

        # ============================
        # SAVE SUCCESS
        # ============================
        print("STEP 6: Saving result")

        generation.result_url = firebase_url
        generation.result_type = result_type
        generation.status = "completed"
        generation.completed_at = timezone.now()
        generation.save()

        print("========== SUCCESS ==========\n")

        return firebase_url

    except Exception as exc:

        print("\n❌ ERROR OCCURRED")
        print("ERROR:", str(exc))
        print("TRACEBACK:", traceback.format_exc())

        generation.retry_count += 1
        generation.save()

        try:
            if isinstance(exc, requests.exceptions.RequestException):
                print("Retrying due to network error...")
                raise self.retry(exc=exc)
            else:
                print("Marking as FAILED (no retry)")
                generation.status = "failed"
                generation.error_message = str(exc)
                generation.completed_at = timezone.now()
                generation.save()

        except self.MaxRetriesExceededError:
            print("Max retries exceeded")

            generation.status = "failed"
            generation.error_message = str(exc)
            generation.completed_at = timezone.now()
            generation.save()