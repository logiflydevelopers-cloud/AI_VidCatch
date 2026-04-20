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
            "count": notifications.count(),
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
        data["notification_type"] = "banner"
        data["message"] = data.get("message", "")
        data["is_active"] = data.get("is_active", True)
        data["trigger_type"] = data.get("trigger_type", "instant")

        # ==========================
        # DISPLAY VALIDATION
        # ==========================
        if data["display_type"] not in ["notification", "slider"]:
            return Response(
                {"error": "display_type must be 'notification' or 'slider'"},
                status=400
            )

        # ==========================
        # TRIGGER VALIDATION
        # ==========================
        trigger_type = data.get("trigger_type")
        trigger_value = data.get("trigger_value")

        if trigger_type in ["after_actions", "delay", "idle"]:
            if trigger_value is None:
                return Response(
                    {"error": f"trigger_value required for {trigger_type}"},
                    status=400
                )

            try:
                data["trigger_value"] = int(trigger_value)
            except ValueError:
                return Response(
                    {"error": "trigger_value must be an integer"},
                    status=400
                )

        # ==========================
        # SLIDER RULE (NO TRIGGERS)
        # ==========================
        if data["display_type"] == "slider":
            data["trigger_type"] = "instant"
            data["trigger_value"] = None

        # ==========================
        # TIME VALIDATION
        # ==========================
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        if start_time and end_time:
            if start_time > end_time:
                return Response(
                    {"error": "start_time cannot be after end_time"},
                    status=400
                )

        # ==========================
        # SERIALIZE & SAVE
        # ==========================
        serializer = NotificationCreateUpdateSerializer(data=data)

        if serializer.is_valid():
            instance = serializer.save()

            return Response({
                "message": "Notification created successfully",
                "data": NotificationSerializer(instance).data
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
                return Response({"error": str(e)}, status=400)

        # ==========================
        # DISPLAY VALIDATION
        # ==========================
        display_type = data.get("display_type", notification.display_type)

        if display_type not in ["notification", "slider"]:
            return Response(
                {"error": "display_type must be 'notification' or 'slider'"},
                status=400
            )

        # ==========================
        # TRIGGER VALIDATION
        # ==========================
        trigger_type = data.get("trigger_type", notification.trigger_type)
        trigger_value = data.get("trigger_value", notification.trigger_value)

        if trigger_type in ["after_actions", "delay", "idle"]:
            if trigger_value is None:
                return Response(
                    {"error": f"trigger_value required for {trigger_type}"},
                    status=400
                )

            try:
                data["trigger_value"] = int(trigger_value)
            except ValueError:
                return Response(
                    {"error": "trigger_value must be an integer"},
                    status=400
                )

        # ==========================
        # SLIDER RULE (NO TRIGGERS)
        # ==========================
        if display_type == "slider":
            data["trigger_type"] = "instant"
            data["trigger_value"] = None

        # ==========================
        # TIME VALIDATION
        # ==========================
        start_time = data.get("start_time", notification.start_time)
        end_time = data.get("end_time", notification.end_time)

        if start_time and end_time:
            if start_time > end_time:
                return Response(
                    {"error": "start_time cannot be after end_time"},
                    status=400
                )

        # ==========================
        # SERIALIZER UPDATE
        # ==========================
        serializer = NotificationCreateUpdateSerializer(
            notification,
            data=data,
            partial=True
        )

        if serializer.is_valid():
            instance = serializer.save()

            return Response({
                "message": "Notification updated successfully",
                "data": NotificationSerializer(instance).data
            })

        return Response(serializer.errors, status=400)

    # ==========================
    # DELETE
    # ==========================
    if request.method == "DELETE":
        notification.delete()
        return Response({"message": "Deleted"}, status=204)