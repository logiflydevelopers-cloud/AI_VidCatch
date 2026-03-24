from django.db import models
import uuid
from apps.users.models import User
from django.utils import timezone
from datetime import timedelta

def generate_sub_id():
    return "sub_" + uuid.uuid4().hex[:8].upper()

def default_end_date():
    return timezone.now() + timedelta(days=30)

class Plan(models.Model):
    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    credits_per_month = models.IntegerField()

    price = models.DecimalField(max_digits=10, decimal_places=2)

    daily_limit = models.IntegerField(null=True, blank=True)

    features = models.JSONField(null=True, blank=True)

    validity_days = models.IntegerField(default=30)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"plan_{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class UserSubscription(models.Model):

    STATUS_CHOICES = (
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    current_plan_id = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    start_date = models.DateTimeField(default=timezone.now)

    end_date = models.DateTimeField(default=default_end_date)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    auto_renew = models.BooleanField(default=False)

    credits_remaining= models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    # ============================
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"sub_{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name