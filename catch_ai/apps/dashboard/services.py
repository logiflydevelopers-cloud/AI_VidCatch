from django.db.models import Count, Sum, Q
from apps.users.models import User
from apps.subscriptions.models import UserSubscription
from apps.generations.models import Generation
from apps.templates.models import AIModel
from apps.credits.models import CreditTransaction


def get_dashboard_data():

    # ==========================================================
    # USERS & SUBSCRIPTIONS (NO FILTERS)
    # ==========================================================
    total_users = User.objects.filter(
        is_staff=False
    ).count()

    total_active_users = User.objects.filter(
        is_active=True, is_staff=False
    ).count()

    total_staff_users = User.objects.filter(
        is_staff=True
    ).count()

    total_subscriptions = UserSubscription.objects.count()

    # ==========================================================
    # GENERATIONS (ALL DATA)
    # ==========================================================
    total_generations = Generation.objects.count()

    # Group by DATE (no restriction)
    all_generations_by_date = Generation.objects.values(
        "created_at__date"
    ).annotate(
        total=Count("id"),

        completed=Count("id", filter=Q(status="completed")),
        failed=Count("id", filter=Q(status="failed")),
        pending=Count("id", filter=Q(status="pending")),
        processing=Count("id", filter=Q(status="processing"))

    ).order_by("created_at__date")

    # ==========================================================
    # MOST USED TEMPLATES (ALL TIME)
    # ==========================================================
    most_used_templates = Generation.objects.filter(
        template__isnull=False
    ).values(
        "template__id",
        "template__name"
    ).annotate(
        usage=Count("id")
    ).order_by("-usage")

    # ==========================================================
    # MODEL USAGE (RAW)
    # ==========================================================
    model_usage = AIModel.objects.values(
        "model_name",
        "name",
        "total_usage_count",
        "total_credits_used"
    ).order_by("-total_usage_count")

    # ==========================================================
    # CREDIT TRANSACTIONS (RAW SPLIT)
    # ==========================================================
    credits_summary = CreditTransaction.objects.values(
        "transaction_type"
    ).annotate(
        total=Sum("amount")
    )

    # ==========================================================
    # FINAL RESPONSE
    # ==========================================================
    return {
        "users": {
            "total_users": total_users,
            "total_active_users": total_active_users,
            "total_staff_users": total_staff_users,
            "total_subscriptions": total_subscriptions
        },

        "generations": {
            "total": total_generations,
            "by_date": list(all_generations_by_date)
        },

        "most_used_templates": list(most_used_templates),

        "models": list(model_usage),

        "credits": list(credits_summary),
    }