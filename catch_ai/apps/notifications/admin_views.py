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
    serializer = NotificationCreateUpdateSerializer(data=request.data)

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