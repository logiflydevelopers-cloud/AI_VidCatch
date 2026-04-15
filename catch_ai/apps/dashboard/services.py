from django.db.models import Count, Sum, Q
from apps.users.models import User
from apps.subscriptions.models import UserSubscription
from apps.generations.models import Generation
from apps.templates.models import AIModel
from apps.credits.models import UserCredits, CreditTransaction
from apps.payments.models import Payment


def get_dashboard_data():

    # ==========================================================
    # USERS & SUBSCRIPTIONS
    # ==========================================================
    total_users = User.objects.filter(is_staff=False).count()

    total_active_users = User.objects.filter(
        is_active=True, is_staff=False
    ).count()

    total_staff_users = User.objects.filter(is_staff=True).count()

    total_subscriptions = UserSubscription.objects.count()

    # ==========================================================
    # USER MANAGEMENT TABLE
    # ==========================================================

    users_qs = User.objects.filter(is_staff=False)

    # 🔹 Credit data (✅ FIXED)
    credits = UserCredits.objects.filter(user__is_staff=False)

    credit_dict = {}
    for c in credits:
        credit_dict[c.user_id] = {
            "used": c.used_credits or 0,
            "balance": c.balance or 0
        }

    # 🔹 Subscription data
    subscriptions = UserSubscription.objects.filter(user__is_staff=False).select_related("current_plan")

    subscription_dict = {}
    for sub in subscriptions:
        subscription_dict[sub.user_id] = {
            "plan_name": sub.current_plan.name if sub.current_plan else "Free",
            "plan_expiry": sub.end_date
        }

    # 🔹 Final user list
    users_list = []

    for user in users_qs:
        sub_data = subscription_dict.get(user.id, {})
        credit_data = credit_dict.get(user.id, {})

        users_list.append({
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
            "status": user.status,
            "last_login": user.last_login,

            "credit_balance": credit_data.get("balance", 0),
            "total_credit_used": credit_data.get("used", 0),

            "plan_name": sub_data.get("plan_name", "Free"),
            "plan_expiry": sub_data.get("plan_expiry"),
        })

    payments_qs = Payment.objects.select_related(
        "user", "plan"
    ).filter(user__is_staff=False).order_by("-created_at")

    payments_list = []

    for p in payments_qs:
        payments_list.append({
            "id": p.id,
            "user_id": p.user.id,
            "email": p.user.email,
            
            "plan_id": p.plan.id,
            "plan_name": p.plan.name if p.plan else "Free",

            "amount": p.amount,
            "status": p.status,
            "provider": p.provider,
            "provider_payment_id": p.provider_payment_id,
            "provider_order_id": p.provider_order_id,

            "created_at": p.created_at,
        })

    credits_qs = CreditTransaction.objects.select_related(
        "user"
    ).filter(user__is_staff=False).order_by("-created_at")

    credits_list = []

    for c in credits_qs:
        credits_list.append({
            "id": c.id,
            "user_id": c.user.id,
            "email": c.user.email,

            "action": c.transaction_action,
            "amount": c.amount,
            "type":c.transaction_type,

            "balance_after": c.balance_after,
            "balance_before": c.balance_before,

            "created_at": c.created_at,
        })

    # ==========================================================
    # GENERATIONS
    # ==========================================================
    total_generations = Generation.objects.count()

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
    # MOST USED TEMPLATES
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
    # MODEL USAGE
    # ==========================================================
    model_usage = AIModel.objects.values(
        "model_name",
        "name",
        "total_usage_count",
        "total_credits_used"
    ).order_by("-total_usage_count")

    # ==========================================================
    # FINAL RESPONSE
    # ==========================================================
    return {
        "users": {
            "total_users": total_users,
            "total_active_users": total_active_users,
            "total_staff_users": total_staff_users,
            "total_subscriptions": total_subscriptions,

            "user_list": users_list
        },

        "payments_transaction": payments_list,
        "credits_transaction": credits_list,

        "generations": {
            "total": total_generations,
            "by_date": list(all_generations_by_date)
        },

        "most_used_templates": list(most_used_templates),
        "models": list(model_usage),
    }