from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Generation(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # user who requested generation
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="generations"
    )

    # template used for generation
    template = models.ForeignKey(
        "templates.Template",
        on_delete=models.CASCADE,
        related_name="generations"
    )

    # user input data (firebase urls + prompt etc)
    input_data = models.JSONField()

    # output media url stored in firebase
    result_url = models.URLField(
        max_length=500,
        null=True,
        blank=True
    )

    # generation status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    # error message if generation fails
    error_message = models.TextField(
        null=True,
        blank=True
    )

    # celery task id (useful for debugging)
    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    # timestamps
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

    def __str__(self):
        return f"Generation {self.id} - {self.user}"