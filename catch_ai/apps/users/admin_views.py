from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from apps.subscriptions.models import UserSubscription
from apps.credits.models import UserCredits

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

@api_view(["GET", "PATCH"])
@permission_classes([IsAdminUser])
def admin_user_detail(request, user_id):

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # ==========================
    # GET → Fetch user data
    # ==========================
    if request.method == "GET":

        subscription = UserSubscription.objects.filter(
            user=user
        ).select_related("current_plan").first()

        credits = UserCredits.objects.filter(user=user).first()

        return Response({
            "id": user.id,
            "name": user.username,
            "email": user.email,

            "status": user.status,
            "is_active": user.is_active,

            "plan": subscription.current_plan.name if subscription and subscription.current_plan else "Free",

            "credits": credits.balance if credits else 0,

            "last_login": user.last_login,
            "created_at": user.created_at
        })

    # ==========================
    # PATCH → Update status
    # ==========================
    if request.method == "PATCH":

        status_value = request.data.get("status")

        if status_value not in ["active", "banned", "new"]:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🚫 BAN always allowed
        if status_value == "banned":
            user.status = "banned"
            user.save(update_fields=["status"])
            return Response({"message": "User banned successfully"})

        # ✅ Check subscription
        has_active_plan = UserSubscription.objects.filter(
            user=user,
            status="active"
        ).exists()

        if status_value == "active" and not has_active_plan:
            return Response(
                {"error": "User does not have active subscription"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Apply status
        user.status = status_value
        user.save(update_fields=["status"])

        return Response({
            "message": "User status updated",
            "status": user.status
        })