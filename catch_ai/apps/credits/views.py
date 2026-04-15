from django.db import transaction
from django.db.models import F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserCredits, CreditTransaction
from apps.templates.models import Template


# ==========================================
# GET USER CREDITS
# ==========================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_credits(request):
    try:
        wallet = request.user.credit_wallet
        remaining = wallet.total_credits - wallet.used_credits
    except UserCredits.DoesNotExist:
        return Response({
            "total_credits": 0,
            "used_credits": 0,
            "remaining_credits": 0
        })

    return Response({
        "total_credits": wallet.total_credits,
        "used_credits": wallet.used_credits,
        "remaining_credits": remaining
    })


# ==========================================
# DEDUCT CREDITS (CORE LOGIC)
# ==========================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deduct_credits_for_template(request):
    template_id = request.data.get("template_id")

    if not template_id:
        return Response({"error": "template_id is required"}, status=400)

    try:
        template = Template.objects.get(id=template_id, is_active=True)
    except Template.DoesNotExist:
        return Response({"error": "Invalid template"}, status=404)

    cost = template.credit_cost

    try:
        wallet = request.user.credit_wallet
    except UserCredits.DoesNotExist:
        return Response({"error": "Wallet not found"}, status=400)

    with transaction.atomic():

        wallet.refresh_from_db()

        # SAFE calculation
        remaining = wallet.total_credits - wallet.used_credits

        if remaining < cost:
            return Response({
                "error": "Not enough credits",
                "required": cost,
                "remaining": remaining
            }, status=400)

        # Deduct safely
        wallet.used_credits = F("used_credits") + cost
        wallet.save(allow_used_update=True)

        # Reload actual values
        wallet.refresh_from_db()

        remaining_after = wallet.total_credits - wallet.used_credits

        # Log transaction
        CreditTransaction.objects.create(
            user=request.user,
            template=template,
            feature=None,
            amount=cost,
            transaction_action="deduct",
            balance_after=remaining_after,
            transaction_action=f"Used template: {template.name}"
        )

    return Response({
        "message": "Credits deducted successfully",
        "remaining_credits": remaining_after
    })


# ==========================================
# ADD CREDITS (OPTIONAL - ADMIN/API)
# ==========================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_credits(request):
    amount = request.data.get("amount")

    if not amount:
        return Response({"error": "amount is required"}, status=400)

    amount = int(amount)

    try:
        wallet = request.user.credit_wallet
    except UserCredits.DoesNotExist:
        wallet = UserCredits.objects.create(user=request.user)

    with transaction.atomic():

        wallet.total_credits = F("total_credits") + amount
        wallet.save()

        wallet.refresh_from_db()

        remaining_after = wallet.total_credits - wallet.used_credits

        CreditTransaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_action="add",
            balance_after=remaining_after,
            transaction_action="Credits added"
        )

    return Response({
        "message": "Credits added",
        "total_credits": wallet.total_credits,
        "remaining_credits": remaining_after
    })