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

    TRIGGER_TYPE_CHOICES = [
        ("instant", "Instant"),
        ("delay", "Delay after open"),
        ("after_actions", "After actions"),
        ("first_video", "After first video"),
        ("idle", "User idle"),
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
    trigger_type = models.CharField(
        max_length=50,
        choices=TRIGGER_TYPE_CHOICES,
        default="instant"
    )

    trigger_value = models.IntegerField(
        null=True,
        blank=True,
        help_text="Seconds / action count depending on trigger"
    )

    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)    

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

        if self.start_time and now < self.start_time:
            return False

        if self.end_time and now > self.end_time:
            return False

        return True
                    
    def __str__(self):
        return self.title
    
class NotificationSeen(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    seen_at = models.DateTimeField(auto_now_add=True)


