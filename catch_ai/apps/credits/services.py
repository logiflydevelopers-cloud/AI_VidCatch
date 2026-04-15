from django.core.exceptions import ValidationError
from django.db import transaction

from .models import UserCredits, CreditTransaction


# ============================
# ADD CREDITS
# ============================
@transaction.atomic
def add_credits(user, amount, transaction_type="Admin reward"):

    amount = int(amount)

    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")

    wallet, _ = UserCredits.objects.get_or_create(user=user)

    before = wallet.balance

    wallet.balance += amount
    wallet.total_credits += amount

    wallet.save()

    CreditTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_action="add",
        balance_before=before,
        balance_after=wallet.balance,
        transaction_type=transaction_type
    )


# ============================
# DEDUCT CREDITS
# ============================
@transaction.atomic
def deduct_credits(user, amount, transaction_type="", template=None, feature=None):

    amount = int(amount)

    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")

    wallet, _ = UserCredits.objects.get_or_create(user=user)

    if wallet.balance < amount:
        raise ValidationError("Insufficient credits")

    before = wallet.balance

    wallet.balance -= amount
    wallet.used_credits += amount

    wallet.save(allow_used_update=True)

    CreditTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_action="deduct",
        balance_before=before,
        balance_after=wallet.balance,
        transaction_type=transaction_type,
        template=template,
        feature=feature
    )


# ============================
# APPLY PLAN PURCHASE
# ============================
@transaction.atomic
def apply_plan_purchase(user, plan):

    wallet, _ = UserCredits.objects.get_or_create(user=user)

    before = wallet.balance

    # RESET WALLET
    wallet.balance = plan.credits_per_month
    wallet.total_credits = plan.credits_per_month
    wallet.used_credits = 0

    wallet.save(allow_used_update=True)

    CreditTransaction.objects.create(
        user=user,
        amount=plan.credits_per_month,
        transaction_action="add",
        balance_before=before,
        balance_after=wallet.balance,
        transaction_type=f"Plan purchase: {plan.name}"
    )


# ============================
# EXPIRE PLAN (RESET ALL CREDITS)
# ============================
@transaction.atomic
def expire_plan(user):

    wallet, _ = UserCredits.objects.get_or_create(user=user)

    # 🚫 Prevent duplicate expiry logs
    if wallet.balance == 0:
        return

    before = wallet.balance

    # ==========================
    # RESET ALL CREDITS
    # ==========================
    wallet.balance = 0
    wallet.used_credits = 0
    wallet.total_credits = 0  # ✅ keep data consistent

    wallet.save()

    # ==========================
    # LOG TRANSACTION
    # ==========================
    CreditTransaction.objects.create(
        user=user,
        amount=before,
        transaction_action="deduct",
        balance_before=before,
        balance_after=0,
        transaction_type="Plan expired - credits reset"
    )