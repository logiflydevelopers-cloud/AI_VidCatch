import os

from celery import Celery


# Set default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catch_ai.settings")


# Create Celery instance
app = Celery("catch_ai")


# Load celery config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")


# Auto discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")