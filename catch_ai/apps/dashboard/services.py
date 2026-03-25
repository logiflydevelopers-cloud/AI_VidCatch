from django.db.models import Count, Sum, F
from django.utils.timezone import now
from datetime import timedelta

from apps.users.models import User
from apps.subscriptions.models import UserSubscription
from apps.generations.models import Generation
from apps.templates.models import AIModel
from apps.credits.models import CreditTransaction


def get_dashboard_data():

    today = now().date()
    last_7_days = today - timedelta(days=7)

    # ==========================================================
    # USERS & SUBSCRIPTIONS
    # ==========================================================
    total_users = User.objects.filter(is_staff=False).count()
    total_active_users = User.objects.filter(is_active=True, is_staff=False).count()

    active_subscriptions = UserSubscription.objects.filter(
        status="active"
    ).count()

    # ==========================================================
    # GENERATIONS
    # ==========================================================
    total_generations = Generation.objects.count()

    today_generations = Generation.objects.filter(
        created_at__date=today
    ).count()

    last_7_days_generations = Generation.objects.filter(
        created_at__date__gte=last_7_days
    ).values("created_at__date").annotate(
        count=Count("id")
    ).order_by("created_at__date")

    # ==========================================================
    # MOST USED TEMPLATES
    # ==========================================================
    most_used_templates = Generation.objects.filter(
        template__isnull=False
    ).values(
        "template__id",
        "template__name"
    ).annotate(
        usage=Count("id")
    ).order_by("-usage")[:5]

    # ==========================================================
    # MODEL USAGE
    # ==========================================================
    model_usage = AIModel.objects.values(
        "model_name",
        "name"
    ).annotate(
        total_usage=F("total_usage_count"),
        total_credits=F("total_credits_used")
    ).order_by("-total_usage")

    # ==========================================================
    # CREDIT USAGE
    # ==========================================================
    total_credits_used = CreditTransaction.objects.filter(
        transaction_type="deduct"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    # ==========================================================
    # FINAL RESPONSE
    # ==========================================================
    return{
        "users": {
            "total_users": total_users,
            "total_active_users": total_active_users,
            "active_subscriptions": active_subscriptions
        },

        "generations": {
            "total": total_generations,
            "today": today_generations,
            "last_7_days": list(last_7_days_generations)
        },

        "templates": list(most_used_templates),

        "models": list(model_usage),

        "credits": {
            "total_used": total_credits_used
        }
    }