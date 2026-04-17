import random
from datetime import timedelta
from django.utils import timezone
from .models import Notification, NotificationTrigger


def handle_app_open(user):
    now = timezone.now()

    # prevent duplicate triggers within 10 min
    exists = NotificationTrigger.objects.filter(
        user=user,
        created_at__gte=now - timedelta(minutes=10)
    ).exists()

    if exists:
        return

    notifications = Notification.objects.filter(
        schedule_type="after_open",
        is_active=True
    )

    for notif in notifications:
        delay = random.randint(notif.delay_min or 5, notif.delay_max or 7)

        trigger_time = now + timedelta(minutes=delay)

        NotificationTrigger.objects.create(
            user=user,
            notification=notif,
            trigger_time=trigger_time
        )