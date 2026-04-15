from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from apps.subscriptions.models import UserSubscription
from apps.credits.models import UserCredits, CreditTransaction
from django.utils import timezone
from django.db import transaction

from apps.users.models import User


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Prevent deleting superuser
    if user.is_superuser:
        return Response(
            {"error": "Cannot delete superuser"},
            status=status.HTTP_403_FORBIDDEN
        )

    user.delete()

    return Response(
        {"message": "User deleted successfully"},
        status=status.HTTP_200_OK
    )

@api_view(["GET", "PATCH", "POST"])
@permission_classes([IsAdminUser])
def admin_user_detail(request, user_id):

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # ==========================
    # GET → USER DETAILS
    # ==========================
    if request.method == "GET":

        subscription = UserSubscription.objects.filter(
            user=user,
            status="active"
        ).select_related("current_plan").first()

        plan_name = "Free"
        if subscription and subscription.current_plan:
            plan_name = subscription.current_plan.name

        last_txn = CreditTransaction.objects.filter(
            user=user
        ).order_by("-created_at").first()

        balance = last_txn.balance_after if last_txn else 0

        return Response({
            "id": user.id,
            "name": user.username,
            "email": user.email,

            "status": user.status,
            "is_active": user.is_active,

            "plan": plan_name,
            "credit_balance": balance,

            "last_login": user.last_login,
            "created_at": user.created_at
        })

    # ==========================
    # PATCH → STATUS + PASSWORD
    # ==========================
    if request.method == "PATCH":

        status_value = request.data.get("status")
        new_password = request.data.get("password")

        update_fields = []

        # 🔐 PASSWORD
        if new_password:
            if len(new_password) < 8:
                return Response({"error": "Password must be at least 8 characters"}, status=400)

            user.set_password(new_password)
            update_fields.append("password")

        # 🔄 STATUS
        if status_value:

            if status_value not in ["active", "banned", "new"]:
                return Response({"error": "Invalid status"}, status=400)

            if status_value == "banned":
                user.status = "banned"
            else:
                has_active_plan = UserSubscription.objects.filter(
                    user=user,
                    status="active"
                ).exists()

                if status_value == "active" and not has_active_plan:
                    return Response({"error": "User has no active subscription"}, status=400)

                user.status = status_value

            update_fields.append("status")

        if not update_fields:
            return Response({"error": "No data provided"}, status=400)

        user.save(update_fields=update_fields)

        return Response({
            "message": "User updated successfully",
            "status": user.status
        })

    # ==========================
    # POST → CREDIT UPDATE
    # ==========================
    if request.method == "POST":

        amount = request.data.get("amount")
        action = request.data.get("action")  # reward / penalty
        description = request.data.get("description", "")

        if not amount or int(amount) <= 0:
            return Response({"error": "Amount must be > 0"}, status=400)

        if action not in ["reward", "penalty"]:
            return Response({"error": "Invalid action"}, status=400)

        amount = int(amount)

        with transaction.atomic():

            last_txn = CreditTransaction.objects.filter(
                user=user
            ).order_by("-created_at").first()

            balance_before = last_txn.balance_after if last_txn else 0

            if action == "reward":
                transaction_action = "add"
                transaction_type = description or "Admin reward"
                balance_after = balance_before + amount

            else:
                transaction_action = "deduct"
                transaction_type = description or "Admin penalty"

                if balance_before < amount:
                    return Response({"error": "Insufficient credits"}, status=400)

                balance_after = balance_before - amount

            CreditTransaction.objects.create(
                user=user,
                amount=amount,
                transaction_action=transaction_action,
                transaction_type=transaction_type,
                balance_before=balance_before,
                balance_after=balance_after,
                created_at=timezone.now()
            )

        return Response({
            "message": "Credits updated successfully",
            "balance_after": balance_after
        })