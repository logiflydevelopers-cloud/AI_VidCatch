# notifications/admin_views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateUpdateSerializer
)

from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import permission_classes
from apps.services.firebase_storage import upload_banner_media


# Get all notifications
@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_all_notifications(request):
    notifications = Notification.objects.all().order_by("-created_at")
    serializer = NotificationSerializer(notifications, many=True)

    return Response({
        "count": len(serializer.data),
        "notifications": serializer.data
    })


# Create notification
@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_notification(request):
    data = request.data.copy()

    # 🔍 DEBUG (remove later)
    print("REQUEST DATA:", data)
    print("FILES:", request.FILES)

    # ==========================================================
    # HANDLE MEDIA UPLOAD
    # ==========================================================
    file = request.FILES.get("media")

    if file:
        try:
            media_url, media_type = upload_banner_media(file)

            data["media"] = media_url
            data["media_type"] = media_type

        except Exception as e:
            return Response(
                {"error": f"Media upload failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ==========================================================
    # FIX: DEFAULT VALUES (VERY IMPORTANT)
    # ==========================================================

    # display_type fix
    if not data.get("display_type"):
        data["display_type"] = "notification"

    # notification_type fix
    if not data.get("notification_type"):
        data["notification_type"] = "banner"

    # message fix (if optional in future)
    if not data.get("message"):
        data["message"] = ""

    # ==========================================================
    # VALIDATION (OPTIONAL BUT STRONG)
    # ==========================================================
    valid_display_types = ["notification", "slider", "both"]

    if data.get("display_type") not in valid_display_types:
        return Response(
            {"error": "Invalid display_type"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ==========================================================
    # SAVE
    # ==========================================================
    serializer = NotificationCreateUpdateSerializer(data=data)

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Notification created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Update notification
@api_view(["PUT"])
@permission_classes([IsAdminUser])
def update_notification(request, notif_id):
    try:
        notification = Notification.objects.get(id=notif_id)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)

    serializer = NotificationCreateUpdateSerializer(
        notification,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Notification updated successfully",
            "data": serializer.data
        })

    return Response(serializer.errors, status=400)


# Delete notification
@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_notification(request, notif_id):
    try:
        notification = Notification.objects.get(id=notif_id)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)

    notification.delete()

    return Response({
        "message": "Notification deleted successfully"
    }, status=204)