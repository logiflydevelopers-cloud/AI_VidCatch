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
        ("cancelled", "Cancelled"),
    )

    PROVIDER_CHOICES = (
        ("stripe", "Stripe"),
        ("razorpay", "Razorpay"),
        ("paypal", "PayPal"),
        ("google_play", "Google Play"),
    )

    # ============================
    # PRIMARY ID
    # ============================
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
    # EXTERNAL IDS (ANTI-FRAUD)
    # ============================
    provider_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True   # 🔥 prevents duplicate purchase reuse
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
    # SAFETY / DEBUGGING
    # ============================
    idempotency_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    raw_response = models.JSONField(
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    failure_reason = models.TextField(
        null=True,
        blank=True
    )

    is_acknowledged = models.BooleanField(default=False)

    refunded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # ============================
    # TIMESTAMPS
    # ============================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # INDEXES (PERFORMANCE)
    # ============================
    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["provider", "provider_payment_id"]),
            models.Index(fields=["created_at"]),
        ]

    # ============================
    # SAVE METHOD
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"pay_{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.status})"


# ==========================================
# PAYMENT EVENT MODEL (AUDIT LOG)
# ==========================================
class PaymentEvent(models.Model):

    EVENT_TYPE = (
        ("created", "Created"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refund", "Refund"),
        ("webhook", "Webhook"),
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="events"
    )

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE
    )

    data = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["payment", "event_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.payment_id} - {self.event_type}"