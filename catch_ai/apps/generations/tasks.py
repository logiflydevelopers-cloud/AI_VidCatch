import requests
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from .models import Generation
from apps.services.firebase_storage import upload_generated_file
from apps.features.models import Features
from apps.credits.models import UserCredits, CreditTransaction


FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id):

    generation = Generation.objects.select_related(
        "template__default_model",
        "feature__default_model",
        "user"
    ).get(id=generation_id)

    cost = 0

    try:
        # ============================
        # SET PROCESSING
        # ============================
        generation.status = "processing"
        generation.started_at = timezone.now()
        generation.save()

        template = generation.template
        feature = generation.feature

        model = None
        schema = None
        prompt_template = None

        # ============================
        # FLOW VALIDATION
        # ============================
        if feature:
            if feature.flow_type == "template" and not template:
                raise Exception("Template flow required before execution")

        # ============================
        # TEMPLATE FLOW
        # ============================
        if template:
            model = template.default_model
            schema = template.input_schema or {}
            prompt_template = getattr(template, "prompt_template", None)

        # ============================
        # FEATURE FLOW
        # ============================
        elif feature:
            model = feature.default_model
            schema = feature.input_schema or {}
            prompt_template = None

        else:
            raise Exception("No template or feature found")

        if not model:
            raise Exception("No default model configured")

        # ============================
        # 🔥 CREDIT CHECK & DEDUCTION (FIXED)
        # ============================
        if template:
            cost = template.credit_cost

            try:
                wallet = generation.user.credit_wallet
            except UserCredits.DoesNotExist:
                raise Exception("User wallet not found")

            with transaction.atomic():
                wallet.refresh_from_db()

                # ✅ ALWAYS manual calculation
                remaining = wallet.total_credits - wallet.used_credits

                if remaining < cost:
                    raise Exception(
                        f"Not enough credits. Required: {cost}, Available: {remaining}"
                    )

                # ✅ Deduct safely
                wallet.used_credits = F("used_credits") + cost
                wallet.save(allow_used_update=True)

                # ✅ Convert expression → real value
                wallet.refresh_from_db()

                remaining_after = wallet.total_credits - wallet.used_credits

                # ✅ Log transaction
                CreditTransaction.objects.create(
                    user=generation.user,
                    template=template,
                    feature=feature if feature else None,
                    amount=cost,
                    transaction_type="deduct",
                    balance_after=remaining_after,
                    description=f"Generation using template: {template.name}"
                )

        # ============================
        # SNAPSHOT
        # ============================
        generation.model_name = model.model_name
        generation.feature_type = model.feature_type
        generation.save()

        # ============================
        # VALIDATE INPUTS
        # ============================
        user_inputs = generation.input_data or {}
        schema_fields = schema.get("fields", [])

        allowed_fields = [f["name"] for f in schema_fields]

        for field in schema_fields:
            if field.get("required") and field["name"] not in user_inputs:
                raise Exception(f"{field['name']} is required")

        clean_inputs = {
            k: v for k, v in user_inputs.items() if k in allowed_fields
        }

        if not clean_inputs:
            raise Exception("Inputs became empty after filtering")

        # ============================
        # PROMPT
        # ============================
        if prompt_template:
            clean_inputs["prompt"] = prompt_template

        # ============================
        # BUILD PAYLOAD
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