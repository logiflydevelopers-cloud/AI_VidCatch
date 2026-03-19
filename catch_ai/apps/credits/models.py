import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class UserCredits(models.Model):

    id = models.CharField(primary_key=True, max_length=30, editable=False)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="credit_wallet"
    )

    total_credits = models.PositiveIntegerField(default=0)   # lifetime purchased
    used_credits = models.PositiveIntegerField(default=0)    # analytics only
    balance = models.PositiveIntegerField(default=0)         # 🔥 MAIN FIELD

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining(self):
        """
        Safe display only (DO NOT use in business logic)
        """
        return self.balance

    def clean(self):
        if isinstance(self.balance, int) and self.balance < 0:
            raise ValidationError("Balance cannot be negative")

    def save(self, *args, **kwargs):
        allow_used_update = kwargs.pop("allow_used_update", False)

        if not self.id:
            self.id = f"crdt-{uuid.uuid4().hex[:8].upper()}"

        # 🔒 Prevent manual tampering of used_credits
        if self.pk and not allow_used_update:
            try:
                old = UserCredits.objects.get(pk=self.pk)
                if old.used_credits != self.used_credits:
                    raise ValidationError("used_credits cannot be modified directly")
            except UserCredits.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - Balance: {self.balance}"
    

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

    # 🔥 NEW (important for audit/debug)
    balance_before = models.PositiveIntegerField(null=True, blank=True)
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