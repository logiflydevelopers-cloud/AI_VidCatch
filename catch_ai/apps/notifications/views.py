# notifications/views.py

from django.utils import timezone
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from .services import handle_app_open

@api_view(["GET"])
def get_active_notifications(request):
    """
    Get all active notifications (banner/push/in-app)
    """

    now = timezone.now()

    notifications = Notification.objects.filter(
        is_active=True
    ).filter(
        Q(start_time__lte=now) | Q(start_time__isnull=True),
        Q(end_time__gte=now) | Q(end_time__isnull=True),
    ).order_by("-priority", "-created_at")

    serializer = NotificationSerializer(notifications, many=True)

    return Response({
        "count": len(serializer.data),
        "notifications": serializer.data
    })


@api_view(["GET"])
def get_active_banner(request):
    """
    Get ONLY top priority banner (for top UI)
    """

    now = timezone.now()

    banner = Notification.objects.filter(
        notification_type="banner",
        is_active=True
    ).filter(
        Q(start_time__lte=now) | Q(start_time__isnull=True),
        Q(end_time__gte=now) | Q(end_time__isnull=True),
    ).order_by("-priority", "-created_at").first()

    if not banner:
        return Response({"banner": None})

    serializer = NotificationSerializer(banner)

    return Response({
        "banner": serializer.data
    })

@api_view(["POST"])
def app_open(request):
    """
    Call this when app starts
    """
    user = request.user

    handle_app_open(user)

    return Response({"message": "App open tracked"})