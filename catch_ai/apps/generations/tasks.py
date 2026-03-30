import requests
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

from apps.features.models import Features
from .models import Generation
from apps.services.firebase_storage import upload_generated_file
from apps.credits.services import deduct_credits, add_credits
from celery.exceptions import MaxRetriesExceededError
from apps.templates.models import GenerationConfig

FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id, payload):

    generation = Generation.objects.select_related(
        "template",
        "feature",
        "user"
    ).get(id=generation_id)

    # ============================
    # IDEMPOTENCY CHECK
    # ============================
    if generation.status == "completed":
        return "Already completed"

    try:
        # ============================
        # COST CALCULATION
        # ============================
        if generation.feature:
            cost = generation.credit_used
        elif generation.template:
            cost = generation.template.credit_cost
        else:
            cost = 1

        if cost <= 0:
            raise Exception("Invalid credit cost")

        # Save cost once
        if not generation.credit_used:
            generation.credit_used = cost

        generation.status = "processing"
        generation.started_at = generation.started_at or timezone.now()
        generation.save(update_fields=["credit_used", "status", "started_at"])

        # ============================
        # CREDIT DEDUCTION
        # ============================
        if not generation.is_credits_deducted:

            deduct_credits(
                user=generation.user,
                amount=cost,
                description=f"Generation ({generation.source_type})",
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
                generation.input_payload.get("image")
                or generation.input_payload.get("image_url")
            )

            if not image:
                raise Exception("Image is required for auto video")

            # 🔥 Build payload from admin config
            payload = {
                "feature": config.feature_type,
                "model": config.model.code,
                "inputs": {
                    "image": image,
                    "image_url": image,
                    "images": [image],
                    "prompt": config.prompt_template
                },
                "settings": config.default_settings or {}
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

        generation.response_payload = data

        ai_result_url = data.get("result_url") or data.get("result")
        if not ai_result_url:
            raise Exception("AI result URL missing")

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
                    description=f"Refund for failed generation {generation.id}"
                )

                generation.is_refunded = True
                generation.save(update_fields=["is_refunded"])

        except Exception as refund_error:
            print("Refund failed:", refund_error)

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
                generation.completed_at = timezone.now()
                generation.save()

            else:
                generation.status = "failed"
                generation.error_message = str(exc)
                generation.completed_at = timezone.now()
                generation.save()

        except MaxRetriesExceededError:
            generation.status = "failed"
            generation.error_message = f"Retries exhausted: {str(exc)}"
            generation.completed_at = timezone.now()
            generation.save()


logger = logging.getLogger(__name__)


@shared_task
def delete_old_generations():
    logger.info("🟡 Task started: delete_old_generations")

    cutoff_date = timezone.now() - timedelta(days=7)
    logger.info(f"⏳ Cutoff time: {cutoff_date}")

    queryset = Generation.objects.filter(created_at__lt=cutoff_date)
    total_to_delete = queryset.count()

    logger.info(f"📊 Records to delete: {total_to_delete}")

    deleted_count, _ = queryset.delete()

    logger.info(f"✅ Deleted {deleted_count} old generations")

    return f"Deleted {deleted_count} old generations"