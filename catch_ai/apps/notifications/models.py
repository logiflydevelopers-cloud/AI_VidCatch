import uuid
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ("banner", "Banner"),
        ("push", "Push"),
        ("email", "Email"),
        ("in_app", "In App"),
    ]

    BANNER_TYPE_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=50,
        editable=False
    )

    # Core Content
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Type of Notification (future scalable)
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES,
        default="banner"
    )

    # Banner specific styling
    banner_type = models.CharField(
        max_length=20,
        choices=BANNER_TYPE_CHOICES,
        default="info"
    )

    # CTA (Call To Action)
    cta_text = models.CharField(max_length=100, blank=True, null=True)
    cta_link = models.URLField(blank=True, null=True)

    # Control flags
    is_active = models.BooleanField(default=True)
    is_dismissible = models.BooleanField(default=True)

    # Scheduling
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)

    # Targeting (future use)
    user_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="e.g. free, premium"
    )

    # Priority (higher shows first)
    priority = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"notif_{uuid.uuid4().hex[:10]}"
        super().save(*args, **kwargs)

    def is_currently_active(self):
        """
        Check if notification should be shown now
        """
        now = timezone.now()

        if not self.is_active:
            return False

        if self.start_time and self.start_time > now:
            return False

        if self.end_time and self.end_time < now:
            return False

        return True

    def __str__(self):
        return f"{self.title} ({self.notification_type})"