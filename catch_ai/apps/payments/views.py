import logging

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


logger = logging.getLogger(__name__)


class PaymentStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_plan(request):
    user = request.user

    plan_id = request.data.get("plan_id")
    purchase_token = request.data.get("purchase_token")
    product_id = request.data.get("product_id")
    order_id = request.data.get("order_id")
    idempotency_key = request.headers.get("Idempotency-Key")

    # ============================
    # VALIDATION
    # ============================
    if not all([plan_id, purchase_token, product_id]):
        return Response(
            {"error": "plan_id, purchase_token, product_id required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ============================
    # IDEMPOTENCY CHECK
    # ============================
    if idempotency_key:
        existing_payment = Payment.objects.filter(
            idempotency_key=idempotency_key,
            status=PaymentStatus.SUCCESS
        ).first()

        if existing_payment:
            return Response({
                "message": "Already processed",
                "payment_id": existing_payment.id
            }, status=200)

    # ============================
    # GET PLAN
    # ============================
    try:
        plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return Response({"error": "Invalid plan"}, status=404)

    # ============================
    # PRODUCT VALIDATION
    # ============================
    if plan.product_id != product_id:
        return Response({"error": "Product mismatch"}, status=400)

    # ============================
    # DUPLICATE PURCHASE CHECK
    # ============================
    if Payment.objects.filter(
        provider="google_play",
        provider_payment_id=purchase_token,
        status=PaymentStatus.SUCCESS
    ).exists():
        return Response({"error": "Purchase already used"}, status=400)

    # ============================
    # CREATE PAYMENT (PENDING)
    # ============================
    payment = Payment.objects.create(
        user=user,
        plan=plan,
        amount=plan.price_inr,
        status=PaymentStatus.PENDING,
        provider="google_play",
        provider_payment_id=purchase_token,
        provider_order_id=order_id,
        idempotency_key=idempotency_key
    )

    logger.info(f"Purchase initiated user={user.id}, plan={plan.id}")

    # ============================
    # VERIFY WITH GOOGLE PLAY
    # ============================
    try:
        if settings.IAP_SANDBOX_MODE:
            verification = {
                "purchaseState": 0,
                "productId": product_id,
                "acknowledgementState": 1
            }
        else:
            verification = verify_android_purchase(
                package_name=settings.GOOGLE_PLAY_PACKAGE_NAME,
                product_id=product_id,
                purchase_token=purchase_token
            )

    except Exception as e:
        logger.error(f"Verification error: {str(e)}")

        payment.status = PaymentStatus.FAILED
        payment.failure_reason = str(e)
        payment.save()

        return Response({"error": "Verification failed"}, status=400)

    if not verification:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Empty verification response"
        payment.save()

        return Response({"error": "Invalid purchase"}, status=400)

    # ============================
    # GOOGLE VALIDATIONS
    # ============================

    # Product match from Google
    if verification.get("productId") != product_id:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Product mismatch from Google"
        payment.save()

        return Response({"error": "Invalid product"}, status=400)

    # Purchase completed
    if verification.get("purchaseState") != 0:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Purchase not completed"
        payment.save()

        return Response({"error": "Purchase not completed"}, status=400)

    # Already consumed (safety)
    if verification.get("consumptionState") == 1:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Already consumed"
        payment.save()

        return Response({"error": "Already consumed"}, status=400)

    # ============================
    # ATOMIC TRANSACTION
    # ============================
    with transaction.atomic():

        # Lock row (race condition protection)
        payment = Payment.objects.select_for_update().get(id=payment.id)

        if payment.status == PaymentStatus.SUCCESS:
            return Response({"message": "Already processed"}, status=200)

        payment.status = PaymentStatus.SUCCESS
        payment.raw_response = verification
        payment.save()

        # ============================
        # SUBSCRIPTION HANDLING
        # ============================
        active_sub = UserSubscription.objects.filter(
            user=user,
            status="active"
        ).first()

        start_date = timezone.now()

        # Extend if active subscription exists
        if active_sub and active_sub.end_date > timezone.now():
            start_date = active_sub.end_date
            active_sub.status = "expired"
            active_sub.save()

        end_date = start_date + timezone.timedelta(days=plan.validity_days)

        UserSubscription.objects.create(
            user=user,
            current_plan=plan,
            start_date=start_date,
            end_date=end_date,
            status="active"
        )

        # ============================
        # APPLY CREDITS
        # ============================
        apply_plan_purchase(user, plan)

    logger.info(f"Purchase success user={user.id}, plan={plan.id}")

    # ============================
    # RESPONSE
    # ============================
    return Response({
        "message": "Plan purchased successfully",
        "payment_id": payment.id,
        "plan": plan.name,
        "credits_added": plan.credits_per_month
    }, status=status.HTTP_200_OK)