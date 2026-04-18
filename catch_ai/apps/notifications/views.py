from django.utils import timezone
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


# ==============================
# SLIDER (CONTINUOUS DISPLAY)
# ==============================
@api_view(["GET"])
def get_slider_notifications(request):
    """
    Get all slider notifications (continuous UI)
    """

    now = timezone.now()

    notifications = Notification.objects.filter(
        is_active=True,
        display_type="slider"
    ).filter(
        Q(start_time__lte=now) | Q(start_time__isnull=True),
        Q(end_time__gte=now) | Q(end_time__isnull=True),
    ).order_by("-priority", "-created_at")

    serializer = NotificationSerializer(notifications, many=True)

    return Response({
        "count": notifications.count(),
        "notifications": serializer.data
    })


# ==============================
# POPUP (TRIGGER-BASED)
# ==============================
@api_view(["GET"])
def get_popup_notifications(request):
    """
    Get popup notifications (frontend will decide when to show)
    """

    now = timezone.now()

    notifications = Notification.objects.filter(
        is_active=True,
        display_type="notification"
    ).filter(
        Q(start_time__lte=now) | Q(start_time__isnull=True),
        Q(end_time__gte=now) | Q(end_time__isnull=True),
    )

    # OPTIONAL BUT IMPORTANT (prevent repeat spam)
    if request.user.is_authenticated:
        seen_ids = request.user.notificationseen_set.values_list(
            "notification_id", flat=True
        )
        notifications = notifications.exclude(id__in=seen_ids)

    notifications = notifications.order_by("-priority", "-created_at")

    serializer = NotificationSerializer(notifications, many=True)

    return Response({
        "count": notifications.count(),
        "notifications": serializer.data
    })
