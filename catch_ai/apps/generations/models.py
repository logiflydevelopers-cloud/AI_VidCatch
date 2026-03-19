import random
import string

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


# ==========================================================
# GENERATE UNIQUE JOB ID
# ==========================================================
def generate_job_id():
    return "job_" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=8)
    )


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
        blank=True,
        db_index=True 
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="generations"
    )

    template = models.ForeignKey(
        "templates.Template",
        on_delete=models.SET_NULL,
        related_name="generations",
        null=True,
        blank=True
    )

    feature = models.ForeignKey(
        "features.Features",
        on_delete=models.SET_NULL,
        related_name="generations",
        null=True,
        blank=True
    )

    source_type = models.CharField(
        max_length=20,
        choices=[("template", "Template"), ("feature", "Feature")],
        null=True,
        blank=True
    )

    # ============================
    # INPUT / OUTPUT
    # ============================
    input_data = models.JSONField()

    result_url = models.URLField(max_length=500, null=True, blank=True)

    result_type = models.CharField(
        max_length=20,
        choices=[("image", "Image"), ("video", "Video")],
        null=True,
        blank=True
    )

    output_metadata = models.JSONField(null=True, blank=True)

    # ============================
    # STATUS TRACKING
    # ============================
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    error_message = models.TextField(null=True, blank=True)

    task_id = models.CharField(max_length=255, null=True, blank=True)

    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    credit_used = models.IntegerField(null=True, blank=True)

    is_credits_deducted = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)

    # ============================
    # SNAPSHOT FIELDS
    # ============================
    model_name = models.CharField(max_length=100, null=True, blank=True)
    feature_type = models.CharField(max_length=50, null=True, blank=True)

    model_provider = models.CharField(max_length=50, null=True, blank=True)

    # ============================
    # PAYLOAD TRACKING
    # ============================
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)

    # ============================
    # OPTIONAL UX FIELD
    # ============================
    input_summary = models.CharField(max_length=255, null=True, blank=True)

    # ============================
    # TIMESTAMPS
    # ============================
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["job_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    # ==========================================================
    # VALIDATION
    # ==========================================================
    def clean(self):
        if not self.template and not self.feature:
            raise ValidationError("Either template or feature must be set")

        if self.template and self.feature:
            raise ValidationError("Only one of template or feature should be set")

    # ==========================================================
    # SAVE
    # ==========================================================
    def save(self, *args, **kwargs):

        # Generate unique job_id
        if not self.job_id:
            for _ in range(5): 
                new_job_id = generate_job_id()
                if not Generation.objects.filter(job_id=new_job_id).exists():
                    self.job_id = new_job_id
                    break

        # Auto source type
        if self.template:
            self.source_type = "template"
        elif self.feature:
            self.source_type = "feature"

        # Auto timestamps
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