import random
import string

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_job_id():
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"job_{code}"


class Generation(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    job_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        blank=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="generations"
    )

    template = models.ForeignKey(
        "templates.Template",
        on_delete=models.CASCADE,
        related_name="generations"
    )

    input_data = models.JSONField()

    result_url = models.URLField(
        max_length=500,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    error_message = models.TextField(
        null=True,
        blank=True
    )

    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.job_id:
            while True:
                job_id = generate_job_id()
                if not Generation.objects.filter(job_id=job_id).exists():
                    self.job_id = job_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_id} - {self.user}"