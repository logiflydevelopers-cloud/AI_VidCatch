import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# ==========================================================
# PAYMENT MODEL
# ==========================================================
class Payment(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    PROVIDER_CHOICES = (
        ("stripe", "Stripe"),
        ("razorpay", "Razorpay"),
        ("paypal", "PayPal"),
    )

    id = models.CharField(
        primary_key=True,
        max_length=30,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    # ============================
    # PLAN LINK
    # ============================
    plan = models.ForeignKey(
        "subscriptions.Plan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # ============================
    # PAYMENT INFO
    # ============================
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=10, default="INR")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES
    )

    # ============================
    # EXTERNAL IDS (IMPORTANT)
    # ============================
    provider_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    provider_order_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    provider_signature = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    # ============================
    # METADATA
    # ============================
    metadata = models.JSONField(null=True, blank=True)

    failure_reason = models.TextField(null=True, blank=True)

    # ============================
    # TIMESTAMPS
    # ============================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"pay_{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.status})"
    

class PaymentEvent(models.Model):

    EVENT_TYPE = (
        ("created", "Created"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refund", "Refund"),
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="events"
    )

    event_type = models.CharField(max_length=20, choices=EVENT_TYPE)

    data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)