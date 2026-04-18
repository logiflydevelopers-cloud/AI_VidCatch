import requests
import traceback
import json

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from apps.features.models import Features
from .models import Generation
from apps.services.firebase_storage import upload_generated_file
from apps.credits.services import deduct_credits, add_credits
from celery.exceptions import MaxRetriesExceededError
from apps.templates.models import GenerationConfig
import random
import re

FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL
logger = logging.getLogger(__name__)

def get_random_prompt(config, last_prompt=None):
    prompts = config.prompt_template or [] 

    if not prompts:
        return ""

    if len(prompts) == 1:
        return prompts[0]

    filtered = [p for p in prompts if p != last_prompt]

    if not filtered:
        filtered = prompts

    return random.choice(filtered)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id, payload):

    generation = Generation.objects.select_related(
        "template",
        "feature",
        "user"
    ).get(id=generation_id)

    logger.info(f"Incoming Payload from frontend: {payload}")

    # ============================
    # IDEMPOTENCY CHECK
    # ============================
    if generation.status == "completed":
        return "Already completed"

    try:
        # ============================
        # COST CALCULATION
        # ============================
        config = None

        if generation.source_type == "auto_video":
            config = GenerationConfig.objects.filter(
                config_type="auto_video",
                is_active=True
            ).first()

            if not config:
                raise Exception("Auto video config not found")

            cost = config.credit_cost

        elif generation.template:
            cost = generation.template.credit_cost

        elif generation.feature:
            cost = generation.credit_used 

        else:
            cost = 1

        if cost <= 0:
            raise Exception("Invalid credit cost")

        if not generation.credit_used:
            generation.credit_used = cost

        generation.status = "processing"
        generation.started_at = generation.started_at or timezone.now()
        generation.save(update_fields=["credit_used", "status", "started_at"])

        # ============================
        # CREDIT DEDUCTION
        # ============================
        if not generation.is_credits_deducted:

            if generation.source_type == "auto_video":
                transaction_type = "Generation (Auto Video)"

            elif generation.template:
                transaction_type = "Generation (Template)"

            elif generation.feature:
                transaction_type = "Generation (Feature)"

            else:
                transaction_type = "Generation"

            deduct_credits(
                user=generation.user,
                amount=cost,
                transaction_type=transaction_type,
                template=generation.template,
                feature=generation.feature
            )

            generation.is_credits_deducted = True
            generation.save(update_fields=["is_credits_deducted"])

        # ============================
        # AUTO VIDEO PAYLOAD OVERRIDE
        # ============================
        if generation.source_type == "auto_video":

            config = GenerationConfig.objects.filter(
                config_type="auto_video",
                is_active=True
            ).first()

            if not config:
                raise Exception("Auto video config not found")

            image = (
                generation.input_data.get("image")
                or generation.input_data.get("image_url")
            )

            if not image:
                raise Exception("Image is required for auto video")

            # ============================
            # SETTINGS (SAFE + MERGE)
            # ============================
            default_settings = config.default_settings or {}

            if isinstance(default_settings, str):
                try:
                    default_settings = json.loads(default_settings)
                except Exception:
                    default_settings = {}

            if not isinstance(default_settings, dict):
                default_settings = {}

            # Merge with incoming payload settings (if any)
            incoming_settings = payload.get("settings") or {}
            settings_data = {**default_settings, **incoming_settings}

            # ============================
            # LAST PROMPT
            # ============================
            last_generation = Generation.objects.filter(
                user=generation.user,
                source_type="auto_video"
            ).exclude(id=generation.id).order_by("-created_at").first()

            last_prompt = last_generation.used_prompt if last_generation else None

            # ============================
            # RANDOM PROMPT
            # ============================
            prompt = get_random_prompt(config, last_prompt)

            if isinstance(prompt, list):
                prompt = random.choice(prompt)

            if not isinstance(prompt, str) or not prompt.strip():
                raise Exception("Invalid or empty prompt")

            prompt = prompt.strip()

            # ✅ SAVE USED PROMPT (VERY IMPORTANT)
            generation.used_prompt = prompt
            generation.save(update_fields=["used_prompt"])

            # ============================
            # FINAL PAYLOAD
            # ============================
            payload = {
                "feature": config.feature_type,
                "model": config.model.model_name if config.model else generation.model_name,
                "inputs": {
                    "image_urls": [image],
                    "prompt": prompt
                },
                "settings": settings_data
            }

            logger.info(f"[AUTO VIDEO] FINAL PAYLOAD: {json.dumps(payload, indent=2)}")

        # ============================
        # ✅ FIX: TEMPLATE BYPASS FEATURE VALIDATION
        # ============================
        if generation.template:
            # Remove feature so FastAPI does NOT validate mapping
            payload["feature"] = generation.feature_type or "image_to_video"

        # ============================
        # CALL FASTAPI
        # ============================  

        if generation.template:

            settings_data = payload.get("settings")

            # If missing → load from DB
            if not settings_data:
                settings_data = generation.template.default_settings

            # Convert string → dict
            if isinstance(settings_data, str):
                settings_data = json.loads(settings_data)

            # Final safety
            if not isinstance(settings_data, dict):
                settings_data = {}

            payload["settings"] = settings_data

        if payload.get("settings"):
            settings = payload["settings"]

            # 🔥 FIX: convert duration
            if "duration" in settings:
                value = settings["duration"]

                if isinstance(value, str):
                    match = re.match(r"(\d+)_sec$", value)
                    if match:
                        settings["duration"] = int(match.group(1))

            payload["settings"] = settings

        logger.info(f"FINAL PAYLOAD TO FASTAPI: {json.dumps(payload, indent=2)}")

        response = requests.post(
            FASTAPI_GENERATE_URL,
            json=payload,
            timeout=600
        )

        try:
            data = response.json()
        except Exception:
            data = {"error": response.text}

        if response.status_code != 200:
            raise Exception(data)

        generation.response_payload = data

        ai_result_url = data.get("result_url") or data.get("result")
        if not ai_result_url:
            raise Exception("AI result URL missing")

        # ============================
        # DETECT RESULT TYPE
        # ============================
        if ai_result_url.endswith((".mp4", ".mov", ".webm")):
            result_type = "video"
        elif ai_result_url.endswith((".png", ".jpg", ".jpeg", ".webp")):
            result_type = "image"
        else:
            result_type = "file"

        # ============================
        # UPLOAD TO FIREBASE
        # ============================
        firebase_url = upload_generated_file(
            ai_result_url,
            generation.user.id
        )

        # ============================
        # SUCCESS
        # ============================
        generation.result_url = firebase_url
        generation.result_type = result_type
        generation.status = "completed"
        generation.completed_at = timezone.now()
        generation.save()

        return firebase_url

    except Exception as exc:
        traceback.print_exc()

        # ============================
        # SAFE REFUND
        # ============================
        try:
            if (
                generation.credit_used
                and generation.is_credits_deducted
                and not generation.is_refunded
            ):
                add_credits(
                    user=generation.user,
                    amount=generation.credit_used,
                    transaction_type=f"Refund for failed generation {generation.id}"
                )

                generation.is_refunded = True
                generation.save(update_fields=["is_refunded"])

        except Exception as refund_error:
            logger.error(f"Refund failed: {refund_error}")

        # ============================
        # RETRY LOGIC
        # ============================
        generation.retry_count += 1
        generation.save(update_fields=["retry_count"])

        try:
            if isinstance(exc, requests.exceptions.RequestException):

                if self.request.retries < self.max_retries:
                    raise self.retry(exc=exc)

                generation.status = "failed"
                generation.error_message = f"Max retries reached: {str(exc)}"

            else:
                generation.status = "failed"
                generation.error_message = (
                    json.dumps(exc, indent=2)
                    if isinstance(exc, dict)
                    else str(exc)
                )

            generation.completed_at = timezone.now()
            generation.save()

        except MaxRetriesExceededError:
            generation.status = "failed"
            generation.error_message = f"Retries exhausted: {str(exc)}"
            generation.completed_at = timezone.now()
            generation.save()


@shared_task
def delete_old_generations():
    logger.info("Task started: delete_old_generations")

    cutoff_date = timezone.now() - timedelta(days=7)
    logger.info(f"Cutoff time: {cutoff_date}")

    queryset = Generation.objects.filter(created_at__lt=cutoff_date)
    total_to_delete = queryset.count()

    logger.info(f"Records to delete: {total_to_delete}")

    deleted_count, _ = queryset.delete()

    logger.info(f"Deleted {deleted_count} old generations")

    return f"Deleted {deleted_count} old generations"

