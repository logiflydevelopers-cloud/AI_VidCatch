import uuid
import random
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings


User = get_user_model()


class Notification(models.Model):

    # ========================
    # CHOICES
    # ========================
    NOTIFICATION_TYPE_CHOICES = [
        ("banner", "Banner"),
        ("push", "Push"),
        ("email", "Email"),
        ("in_app", "In App"),
    ]

    DISPLAY_TYPE_CHOICES = [
        ("notification", "Notification"),
        ("slider", "Slider"),
        ("both", "Both"),
    ]

    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
    ]

    SCHEDULE_TYPE_CHOICES = [
        ("instant", "Instant"),
        ("once", "One Time"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("after_open", "After App Open"),
    ]

    # ========================
    # CORE
    # ========================
    id = models.CharField(primary_key=True, max_length=50, editable=False)

    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES,
        default="banner"
    )

    display_type = models.CharField(
        max_length=20,
        choices=DISPLAY_TYPE_CHOICES,
        default="notification"
    )

    media = models.URLField(blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, blank=True, null=True)

    # ========================
    # CONTROL
    # ========================
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    # ========================
    # SCHEDULING
    # ========================
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        default="instant"
    )

    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)

    day_of_week = models.IntegerField(blank=True, null=True)  # 0=Monday, 6=Sunday
    time_of_day = models.TimeField(blank=True, null=True)

    delay_min = models.IntegerField(blank=True, null=True)
    delay_max = models.IntegerField(blank=True, null=True)

    last_sent_at = models.DateTimeField(blank=True, null=True)

    # ========================
    # TARGETING
    # ========================
    user_type = models.CharField(max_length=50, blank=True, null=True)

    # ========================
    # META
    # ========================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ========================
    # SAVE
    # ========================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"notif_{uuid.uuid4().hex[:10]}"
        super().save(*args, **kwargs)

    # ========================
    # ACTIVE CHECK (SAFE)
    # ========================
    def is_currently_active(self):
        now = timezone.now()

        if not self.is_active:
            return False

        # One-time
        if self.schedule_type == "once":
            if self.start_time and self.start_time > now:
                return False

        # Daily
        elif self.schedule_type == "daily":
            if self.time_of_day:
                return now.time() >= self.time_of_day

        # Weekly
        elif self.schedule_type == "weekly":
            if self.day_of_week is not None and self.time_of_day:
                return (
                    now.weekday() == self.day_of_week and
                    now.time() >= self.time_of_day
                )

    def __str__(self):
        return self.title
    
class NotificationTrigger(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)

    trigger_time = models.DateTimeField()
    is_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

