import requests
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from apps.features.models import Features
from .models import Generation
from apps.services.firebase_storage import upload_generated_file
from apps.credits.services import deduct_credits, add_credits
from celery.exceptions import MaxRetriesExceededError


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


@shared_task
def delete_old_generations():
    cutoff_date = timezone.now() - timedelta(days=7)

    deleted_count, _ = Generation.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    return f"Deleted {deleted_count} old generations"