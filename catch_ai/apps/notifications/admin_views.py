from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateUpdateSerializer
)

from apps.services.firebase_storage import upload_banner_media


# ==========================================================
# LIST + CREATE
# ==========================================================
@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def notifications(request):

    # ==========================
    # GET → LIST
    # ==========================
    if request.method == "GET":
        notifications = Notification.objects.all().order_by("-created_at")
        serializer = NotificationSerializer(notifications, many=True)

        return Response({
            "count": len(serializer.data),
            "notifications": serializer.data
        })

    # ==========================
    # POST → CREATE
    # ==========================
    if request.method == "POST":

        data = request.data.copy()

        # ==========================
        # MEDIA UPLOAD
        # ==========================
        file = request.FILES.get("media")

        if file:
            try:
                media_url, media_type = upload_banner_media(file)
                data["media"] = media_url
                data["media_type"] = media_type
            except Exception as e:
                return Response(
                    {"error": f"Media upload failed: {str(e)}"},
                    status=400
                )

        # ==========================
        # DEFAULT VALUES
        # ==========================
        data["display_type"] = data.get("display_type", "notification")
        data["notification_type"] = data.get("notification_type", "banner")
        data["message"] = data.get("message", "")

        # ==========================
        # VALIDATION
        # ==========================
        if data["display_type"] not in ["notification", "slider", "both"]:
            return Response({"error": "Invalid display_type"}, status=400)

        serializer = NotificationCreateUpdateSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Notification created successfully",
                "data": serializer.data
            }, status=201)

        return Response(serializer.errors, status=400)
    
    
    
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAdminUser])
def notification_detail(request, notif_id):

    try:
        notification = Notification.objects.get(id=notif_id)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)

    # ==========================
    # GET → SINGLE
    # ==========================
    if request.method == "GET":
        return Response(NotificationSerializer(notification).data)

    # ==========================
    # PATCH → UPDATE
    # ==========================
    if request.method == "PATCH":

        data = request.data.copy()

        file = request.FILES.get("media")

        if file:
            try:
                media_url, media_type = upload_banner_media(file)
                data["media"] = media_url
                data["media_type"] = media_type
            except Exception as e:
                return Response({"error": str(e)}, status=400)

        serializer = NotificationCreateUpdateSerializer(
            notification,
            data=data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Notification updated successfully",
                "data": serializer.data
            })

        return Response(serializer.errors, status=400)

    # ==========================
    # DELETE
    # ==========================
    if request.method == "DELETE":
        notification.delete()
        return Response({"message": "Deleted"}, status=204)