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
from apps.features.utils import calculate_feature_cost


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
        # COST + MODEL
        # ============================
        if generation.feature:

            # get mode from payload
            mode = payload.get("quality")  # fast / standard / advanced
            options = payload.get("settings", {})

            allowed_modes = ["fast", "standard", "advanced"]

            if generation.feature.is_multi_mode:
                if mode not in allowed_modes:
                    raise Exception(f"Invalid quality. Allowed: {allowed_modes}")

            # fallback to default model mapping if needed
            if not mode and generation.feature.is_multi_mode:
                mode = "standard"

            # calculate dynamic cost
            cost = calculate_feature_cost(
                feature=generation.feature,
                mode=mode,
                options=options  # includes generate_audio etc.
            )

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
        # CREDIT DEDUCTION
        # ============================
        if not generation.is_credits_deducted:

            with transaction.atomic():
                wallet = UserCredits.objects.select_for_update().get(
                    user=generation.user
                )

                available_credits = wallet.total_credits - wallet.used_credits

                if available_credits < cost:
                    raise Exception(
                        f"Not enough credits. Required: {cost}, Available: {available_credits}"
                    )

                before = available_credits

                UserCredits.objects.filter(id=wallet.id).update(
                    used_credits=F("used_credits") + cost
                )

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
                with transaction.atomic():
                    wallet = UserCredits.objects.select_for_update().get(
                        user=generation.user
                    )

                    before = wallet.total_credits - wallet.used_credits

                    UserCredits.objects.filter(id=wallet.id).update(
                        used_credits=F("used_credits") - generation.credit_used
                    )

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