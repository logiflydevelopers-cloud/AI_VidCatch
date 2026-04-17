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
        data["schedule_type"] = data.get("schedule_type", "instant")
        data["is_active"] = data.get("is_active", True)

        # ==========================
        # BASIC VALIDATION
        # ==========================
        if data["display_type"] not in ["notification", "slider", "both"]:
            return Response({"error": "Invalid display_type"}, status=400)

        schedule_type = data.get("schedule_type")

        # ==========================
        # SCHEDULING VALIDATION
        # ==========================

        # ONE TIME
        if schedule_type == "once":
            if not data.get("start_time"):
                return Response(
                    {"error": "start_time required for one-time notification"},
                    status=400
                )

        # DAILY
        if schedule_type == "daily":
            if not data.get("time_of_day"):
                return Response(
                    {"error": "time_of_day required for daily notification"},
                    status=400
                )
            data["start_time"] = None  # avoid confusion

        # WEEKLY
        if schedule_type == "weekly":
            if data.get("day_of_week") is None or not data.get("time_of_day"):
                return Response(
                    {"error": "day_of_week and time_of_day required for weekly"},
                    status=400
                )
            data["start_time"] = None

        # AFTER APP OPEN
        if schedule_type == "after_open":
            delay_min = data.get("delay_min")
            delay_max = data.get("delay_max")

            if delay_min is None or delay_max is None:
                return Response(
                    {"error": "delay_min and delay_max required for after_open"},
                    status=400
                )

            try:
                delay_min = int(delay_min)
                delay_max = int(delay_max)
            except ValueError:
                return Response(
                    {"error": "delay_min and delay_max must be integers"},
                    status=400
                )

            if delay_min > delay_max:
                return Response(
                    {"error": "delay_min cannot be greater than delay_max"},
                    status=400
                )

            data["start_time"] = None
            data["end_time"] = None

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
        # GET FINAL SCHEDULE TYPE
        # ==========================
        schedule_type = data.get("schedule_type", notification.schedule_type)

        # ==========================
        # SCHEDULING VALIDATION
        # ==========================

        # ONE TIME
        if schedule_type == "once":
            if not data.get("start_time") and not notification.start_time:
                return Response(
                    {"error": "start_time required for one-time notification"},
                    status=400
                )

        # DAILY
        if schedule_type == "daily":
            if not data.get("time_of_day") and not notification.time_of_day:
                return Response(
                    {"error": "time_of_day required for daily notification"},
                    status=400
                )
            data["start_time"] = None

        # WEEKLY
        if schedule_type == "weekly":
            if (
                data.get("day_of_week") is None and notification.day_of_week is None
            ) or (
                not data.get("time_of_day") and not notification.time_of_day
            ):
                return Response(
                    {"error": "day_of_week and time_of_day required for weekly"},
                    status=400
                )
            data["start_time"] = None

        # AFTER APP OPEN
        if schedule_type == "after_open":
            delay_min = data.get("delay_min", notification.delay_min)
            delay_max = data.get("delay_max", notification.delay_max)

            if delay_min is None or delay_max is None:
                return Response(
                    {"error": "delay_min and delay_max required"},
                    status=400
                )

            try:
                delay_min = int(delay_min)
                delay_max = int(delay_max)
            except ValueError:
                return Response(
                    {"error": "delay_min and delay_max must be integers"},
                    status=400
                )

            if delay_min > delay_max:
                return Response(
                    {"error": "delay_min cannot be greater than delay_max"},
                    status=400
                )

            data["start_time"] = None
            data["end_time"] = None

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

            # 🔥 IMPORTANT: reset last_sent_at if scheduling changed
            if "schedule_type" in data or "time_of_day" in data or "day_of_week" in data:
                instance.last_sent_at = None
                instance.save(update_fields=["last_sent_at"])

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