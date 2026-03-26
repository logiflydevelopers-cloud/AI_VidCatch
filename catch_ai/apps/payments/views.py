from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import Payment
from apps.subscriptions.models import Plan, UserSubscription
from apps.credits.services import apply_plan_purchase
from .google_play import verify_android_purchase


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_plan(request):
    user = request.user

    plan_id = request.data.get("plan_id")
    purchase_token = request.data.get("purchase_token")
    product_id = request.data.get("product_id")
    order_id = request.data.get("order_id")

    # ============================
    # VALIDATION
    # ============================
    if not all([plan_id, purchase_token, product_id]):
        return Response(
            {"error": "plan_id, purchase_token, product_id required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ============================
    # GET PLAN
    # ============================
    try:
        plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return Response({"error": "Invalid plan"}, status=404)

    # ============================
    # PRODUCT VALIDATION (ANTI-FRAUD)
    # ============================
    if plan.product_id != product_id:
        return Response({"error": "Product mismatch"}, status=400)

    # ============================
    # PREVENT DUPLICATE PURCHASE
    # ============================
    if Payment.objects.filter(
        provider="google_play",
        provider_payment_id=purchase_token,
        status="success"
    ).exists():
        return Response({"error": "Purchase already used"}, status=400)

    # ============================
    # PREVENT SAME ACTIVE PLAN
    # ============================
    active_sub = UserSubscription.objects.filter(
        user=user,
        status="active"
    ).first()

    if active_sub and active_sub.current_plan == plan:
        return Response({"error": "Already subscribed to this plan"}, status=400)

    # ============================
    # CREATE PAYMENT (PENDING)
    # ============================
    payment = Payment.objects.create(
        user=user,
        plan=plan,
        amount=plan.price_inr,
        status="pending",
        provider="google_play",
        provider_payment_id=purchase_token,
        provider_order_id=order_id
    )

    # ============================
    # VERIFY WITH GOOGLE PLAY / SANDBOX
    # ============================
    package_name = settings.GOOGLE_PLAY_PACKAGE_NAME

    if settings.IAP_SANDBOX_MODE or request.user.is_staff:
        verification = {"purchaseState": 0}
    else:
        verification = verify_android_purchase(
            package_name=package_name,
            product_id=product_id,
            purchase_token=purchase_token
        )

    if not verification:
        payment.status = "failed"
        payment.failure_reason = "Verification failed"
        payment.save()

        return Response({"error": "Invalid purchase"}, status=400)

    # ============================
    # VALIDATE PURCHASE STATE
    # ============================
    if verification.get("purchaseState") != 0:
        payment.status = "failed"
        payment.failure_reason = "Purchase not completed"
        payment.save()

        return Response({"error": "Purchase not completed"}, status=400)

    # ============================
    # ATOMIC TRANSACTION (CRITICAL)
    # ============================
    with transaction.atomic():

        # MARK PAYMENT SUCCESS
        payment.status = "success"
        payment.save()

        # DEACTIVATE OLD SUBSCRIPTIONS
        UserSubscription.objects.filter(
            user=user,
            status="active"
        ).update(status="expired")

        # CREATE NEW SUBSCRIPTION
        UserSubscription.objects.create(
            user=user,
            current_plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            status="active"
        )

        # APPLY CREDITS
        apply_plan_purchase(user, plan)

    # ============================
    # RESPONSE
    # ============================
    return Response({
        "message": "Plan purchased successfully",
        "payment_id": payment.id,
        "plan": plan.name,
        "credits_added": plan.credits_per_month
    }, status=status.HTTP_200_OK)