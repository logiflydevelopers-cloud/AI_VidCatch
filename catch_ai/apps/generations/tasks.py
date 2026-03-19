import requests
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from apps.features.models import Features 
from .models import Generation
from apps.services.firebase_storage import upload_generated_file
from apps.credits.models import UserCredits, CreditTransaction



FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id, payload):

    generation = Generation.objects.select_related(
        "template",
        "feature",
        "model",   # ✅ IMPORTANT (make sure this FK exists)
        "user"
    ).get(id=generation_id)

    # ============================
    # ✅ IDEMPOTENCY CHECK
    # ============================
    if generation.status == "completed":
        return "Already completed"

    try:
        # ============================
        # ✅ DETERMINE COST (FIXED)
        # ============================
        # ============================
        # ✅ DETERMINE COST + VALIDATE MODEL
        # ============================
        if generation.feature:

            # validate model
            if generation.model:
                if generation.model not in generation.feature.allowed_models.all():
                    raise Exception("Invalid model for this feature")
            else:
                # fallback to default model
                generation.model = generation.feature.default_model
                generation.save(update_fields=["model"])

            cost = generation.feature.credit_cost

        elif generation.template:
            cost = generation.template.credit_cost

        else:
            cost = 1

        if cost <= 0:
            raise Exception("Invalid credit cost")

        # Save cost only once
        if not generation.credit_used:
            generation.credit_used = cost

        generation.status = "processing"
        generation.started_at = generation.started_at or timezone.now()
        generation.save(update_fields=["credit_used", "status", "started_at"])

        # ============================
        # ✅ CREDIT DEDUCTION (FIXED)
        # ============================
        if not generation.is_credits_deducted:

            with transaction.atomic():
                wallet = UserCredits.objects.select_for_update().get(
                    user=generation.user
                )

                # 🔥 CORRECT CREDIT CALCULATION
                available_credits = wallet.total_credits - wallet.used_credits

                if available_credits < cost:
                    raise Exception(
                        f"Not enough credits. Required: {cost}, Available: {available_credits}"
                    )

                before = available_credits

                # ✅ Deduct ONLY from used_credits
                wallet.used_credits = F("used_credits") + cost
                wallet.save()

                wallet.refresh_from_db()

                after = wallet.total_credits - wallet.used_credits

                CreditTransaction.objects.create(
                    id=f"txn_{generation.id}",
                    user=generation.user,
                    template=generation.template,
                    feature=generation.feature,
                    amount=cost,
                    transaction_type="deduct",
                    balance_before=before,
                    balance_after=after,
                    description=f"Generation ({generation.source_type})"
                )

                # mark deducted
                generation.is_credits_deducted = True
                generation.save(update_fields=["is_credits_deducted"])

        # ============================
        # ✅ CALL FASTAPI
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

        result_type = data.get("type", "image")

        # ============================
        # ✅ UPLOAD TO FIREBASE
        # ============================
        firebase_url = upload_generated_file(
            ai_result_url,
            generation.user.id
        )

        # ============================
        # ✅ SUCCESS
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
        # 🔥 SAFE REFUND (FIXED)
        # ============================
        try:
            if (
                generation.credit_used
                and generation.is_credits_deducted
                and not generation.is_refunded
            ):
                with transaction.atomic():
                    wallet = UserCredits.objects.select_for_update().get(
                        user=generation.user
                    )

                    before = wallet.total_credits - wallet.used_credits

                    # ✅ refund by reducing used_credits
                    wallet.used_credits = F("used_credits") - generation.credit_used
                    wallet.save()

                    wallet.refresh_from_db()

                    after = wallet.total_credits - wallet.used_credits

                    CreditTransaction.objects.create(
                        user=generation.user,
                        amount=generation.credit_used,
                        transaction_type="add",
                        balance_before=before,
                        balance_after=after,
                        description=f"Refund for failed generation {generation.id}"
                    )

                    # mark refunded
                    generation.is_refunded = True
                    generation.save(update_fields=["is_refunded"])

        except Exception as refund_error:
            print("Refund failed:", refund_error)

        generation.retry_count += 1
        generation.save(update_fields=["retry_count"])

        try:
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