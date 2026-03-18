import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


# ============================
# USER CREDIT WALLET
# ============================
class UserCredits(models.Model):

    id = models.CharField(primary_key=True, max_length=30, editable=False)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="credit_wallet"
    )

    total_credits = models.PositiveIntegerField(default=0)
    used_credits = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # SAFE PROPERTY (ONLY FOR DISPLAY)
    @property
    def remaining(self):
        """
        Use ONLY for display (admin, serializer).
        NEVER use inside business logic with F() expressions.
        """
        if isinstance(self.used_credits, int):
            return self.total_credits - self.used_credits
        return None  # avoid crash if expression

    def clean(self):
        # Only validate when actual values (not F expressions)
        if isinstance(self.used_credits, int):
            if self.used_credits > self.total_credits:
                raise ValidationError("Used credits cannot exceed total credits")

    def save(self, *args, **kwargs):
        allow_used_update = kwargs.pop("allow_used_update", False)

        if not self.id:
            self.id = f"crdt-{uuid.uuid4().hex[:8].upper()}"

        # 🔒 Prevent manual modification
        if self.pk and not allow_used_update:
            try:
                old = UserCredits.objects.get(pk=self.pk)
                if old.used_credits != self.used_credits:
                    raise ValidationError("used_credits cannot be modified directly")
            except UserCredits.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.total_credits - self.used_credits} credits"


# ============================
# CREDIT TRANSACTIONS
# ============================
class CreditTransaction(models.Model):

    TRANSACTION_TYPE = (
        ("add", "Add"),
        ("deduct", "Deduct"),
    )

    id = models.CharField(primary_key=True, max_length=30, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="credit_transactions"
    )

    template = models.ForeignKey(
        "templates.Template",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    feature = models.ForeignKey(
        "features.Features",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)

    balance_after = models.PositiveIntegerField(null=True, blank=True)

    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"trxn-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.transaction_type})"