import requests

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Generation
from apps.services.firebase_storage import upload_generated_image


FASTAPI_GENERATE_URL = settings.FASTAPI_GENERATE_URL

@shared_task
def test_task():
    print("Celery task executed successfully!")


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_generation(self, generation_id):
    """
    Celery task to process AI generation.
    """

    try:
        generation = Generation.objects.get(id=generation_id)

        # mark as processing
        generation.status = "processing"
        generation.started_at = timezone.now()
        generation.save()

        payload = generation.input_data

        # call FastAPI AI server
        response = requests.post(
            FASTAPI_GENERATE_URL,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception("AI server returned error")

        data = response.json()

        ai_result_url = data.get("result_url")

        if not ai_result_url:
            raise Exception("AI result URL missing")

        # download AI image and upload to Firebase
        firebase_url = upload_generated_image(
            ai_result_url,
            generation.user.id
        )

        # update generation
        generation.result_url = firebase_url
        generation.status = "completed"
        generation.completed_at = timezone.now()
        generation.save()

        return firebase_url

    except Exception as exc:

        # retry if possible
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:

            generation = Generation.objects.get(id=generation_id)

            generation.status = "failed"
            generation.error_message = str(exc)
            generation.completed_at = timezone.now()
            generation.save()