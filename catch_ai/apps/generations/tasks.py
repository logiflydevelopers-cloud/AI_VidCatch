import requests
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from .models import Generation
from apps.services.firebase_storage import upload_generated_file
from apps.credits.models import UserCredits, CreditTransaction


FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id, payload):

    generation = Generation.objects.select_related(
        "template",
        "feature",
        "user"
    ).get(id=generation_id)

    cost = generation.credit_used or 1

    try:
        # ============================
        # SET PROCESSING
        # ============================
        generation.status = "processing"
        generation.started_at = timezone.now()
        generation.save()

        # ============================
        # CREDIT CHECK & DEDUCTION
        # ============================
        try:
            wallet = generation.user.credit_wallet
        except UserCredits.DoesNotExist:
            raise Exception("User wallet not found")

        with transaction.atomic():
            wallet.refresh_from_db()

            remaining = wallet.total_credits - wallet.used_credits

            if remaining < cost:
                raise Exception(
                    f"Not enough credits. Required: {cost}, Available: {remaining}"
                )

            wallet.used_credits = F("used_credits") + cost
            wallet.save(allow_used_update=True)
            wallet.refresh_from_db()

            remaining_after = wallet.total_credits - wallet.used_credits

            CreditTransaction.objects.create(
                user=generation.user,
                template=generation.template,
                feature=generation.feature,
                amount=cost,
                transaction_type="deduct",
                balance_after=remaining_after,
                description=f"Generation ({generation.source_type})"
            )

        # ============================
        # CALL FASTAPI (🔥 CLEAN)
        # ============================
        response = requests.post(
            FASTAPI_GENERATE_URL,
            json=payload,
            timeout=300
        )

        response.raise_for_status()
        data = response.json()

        # ============================
        # STORE RESPONSE PAYLOAD
        # ============================
        generation.response_payload = data

        ai_result_url = data.get("result_url") or data.get("result")

        if not ai_result_url:
            raise Exception("AI result URL missing")

        result_type = data.get("type", "image")

        # ============================
        # UPLOAD TO FIREBASE
        # ============================
        firebase_url = upload_generated_file(
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
        traceback.print_exc()

        generation.retry_count += 1
        generation.save()

        try:
            # Retry only for network/API issues
            if isinstance(exc, requests.exceptions.RequestException):
                raise self.retry(exc=exc)

            else:
                generation.status = "failed"
                generation.error_message = str(exc)
                generation.completed_at = timezone.now()
                generation.save()

        except self.MaxRetriesExceededError:
            generation.status = "failed"
            generation.error_message = str(exc)
            generation.completed_at = timezone.now()
            generation.save()