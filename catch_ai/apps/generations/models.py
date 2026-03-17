import random
import string

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# ==========================================================
# GENERATE UNIQUE JOB ID
# ==========================================================
def generate_job_id():
    return "job_" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=8)
    )


# ==========================================================
# GENERATION MODEL
# ==========================================================
class Generation(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # ✅ FIXED (NO DEFAULT VALUE)
    job_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
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

    result_type = models.CharField(
        max_length=20,
        choices=[("image", "Image"), ("video", "Video")],
        null=True,
        blank=True
    )

    output_metadata = models.JSONField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    error_message = models.TextField(null=True, blank=True)

    task_id = models.CharField(max_length=255, null=True, blank=True)

    retry_count = models.IntegerField(default=0)

    credit_used = models.IntegerField(default=1)

    # snapshot fields
    model_name = models.CharField(max_length=100, null=True, blank=True)
    feature_type = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["job_id"]),
        ]

    # ==========================================================
    # OVERRIDE SAVE
    # ==========================================================
    def save(self, *args, **kwargs):

        # ✅ Generate unique job_id
        if not self.job_id:
            while True:
                new_job_id = generate_job_id()
                if not Generation.objects.filter(job_id=new_job_id).exists():
                    self.job_id = new_job_id
                    break

        # ✅ Auto timestamps
        if self.status == "processing" and not self.started_at:
            self.started_at = timezone.now()

        if self.status in ["completed", "failed"] and not self.completed_at:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    # ==========================================================
    # PROCESSING TIME
    # ==========================================================
    @property
    def processing_time(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __str__(self):
        return f"{self.job_id} - {self.user}"