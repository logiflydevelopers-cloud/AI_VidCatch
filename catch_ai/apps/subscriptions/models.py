from django.db import models
import uuid
from apps.users.models import User
from django.utils import timezone
from datetime import timedelta


# ============================
# HELPERS
# ============================

def generate_plan_id():
    return "plan_" + uuid.uuid4().hex[:6].upper()


def generate_sub_id():
    return "sub_" + uuid.uuid4().hex[:8].upper()


def default_end_date():
    return timezone.now() + timedelta(days=30)


# ============================
# PLAN MODEL
# ============================

class Plan(models.Model):

    id = models.CharField(
        primary_key=True,
        max_length=20,
        editable=False
    )

    name = models.CharField(max_length=255)

    credits_per_month = models.IntegerField(default=0)

    price_inr = models.DecimalField(max_digits=10, decimal_places=2)

    daily_limit = models.IntegerField(null=True, blank=True)

    features = models.JSONField(null=True, blank=True)

    validity_days = models.IntegerField(default=30)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    product_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # ======================================
    # SAVE
    # ======================================
    def save(self, *args, **kwargs):

        if not self.id:
            self.id = generate_plan_id()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# ============================
# USER SUBSCRIPTION MODEL
# ============================

class UserSubscription(models.Model):

    STATUS_CHOICES = (
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    id = models.CharField(
        primary_key=True,
        max_length=20,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    current_plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_subscriptions"
    )

    start_date = models.DateTimeField(default=timezone.now)

    end_date = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    auto_renew = models.BooleanField(default=False)

    credits_remaining = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    # ============================
    # SAVE LOGIC
    # ============================
    def save(self, *args, **kwargs):

        # Generate ID
        if not self.id:
            self.id = generate_sub_id()

        # Set end_date based on plan validity
        if self.current_plan and not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.current_plan.validity_days)

        # Set initial credits
        if self.current_plan and self.credits_remaining == 0:
            self.credits_remaining = self.current_plan.credits_per_month

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.current_plan} ({self.status})"