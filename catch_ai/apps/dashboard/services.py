from django.db.models import Count, Sum, Q
from apps.users.models import User
from apps.subscriptions.models import UserSubscription
from apps.generations.models import Generation
from apps.templates.models import AIModel
from apps.credits.models import UserCredits, CreditTransaction
from apps.payments.models import Payment


from django.db.models import Count, Sum, Q
from django.db.models.functions import Lower

def get_dashboard_data():

    # ==========================================================
    # USERS (OPTIMIZED - SINGLE QUERY)
    # ==========================================================
    user_stats = User.objects.aggregate(
        total_users=Count("id", filter=Q(is_staff=False)),
        total_active_users=Count("id", filter=Q(is_active=True, is_staff=False)),
        total_staff_users=Count("id", filter=Q(is_staff=True)),
        banned_users=Count("id", filter=Q(status="banned"))
    )

    total_users = user_stats["total_users"]
    total_active_users = user_stats["total_active_users"]
    total_staff_users = user_stats["total_staff_users"]
    banned_users = user_stats["banned_users"]

    total_subscriptions = UserSubscription.objects.count()

    # ==========================================================
    # USERS LIST (LIMITED + OPTIMIZED)
    # ==========================================================
    users_qs = User.objects.filter(is_staff=False).order_by("-created_at")[:50]

    credits = UserCredits.objects.filter(user__is_staff=False).values(
        "user_id", "used_credits", "balance"
    )

    credit_dict = {
        c["user_id"]: {
            "used": c["used_credits"] or 0,
            "balance": c["balance"] or 0
        } for c in credits
    }

    subscriptions = UserSubscription.objects.filter(
        user__is_staff=False
    ).select_related("current_plan").values(
        "user_id", "end_date", "current_plan__name"
    )

    subscription_dict = {
        s["user_id"]: {
            "plan_name": s["current_plan__name"] or "Free",
            "plan_expiry": s["end_date"]
        } for s in subscriptions
    }

    users_list = []
    for user in users_qs:
        sub_data = subscription_dict.get(user.id, {})
        credit_data = credit_dict.get(user.id, {})

        users_list.append({
            "id": user.id,
            "email": user.email,
            "name": user.username,
            "created_at": user.created_at,
            "status": user.status,
            "last_login": user.last_login,

            "credit_balance": credit_data.get("balance", 0),
            "total_credit_used": credit_data.get("used", 0),

            "plan_name": sub_data.get("plan_name", "Free"),
            "plan_expiry": sub_data.get("plan_expiry"),
        })

    # ==========================================================
    # PAYMENTS (LIMITED + NO N+1)
    # ==========================================================
    payments_qs = Payment.objects.select_related(
        "user", "plan"
    ).filter(user__is_staff=False).order_by("-created_at")[:50]

    payments_list = []

    for p in payments_qs:
        payments_list.append({
            "id": p.id,
            "user_id": p.user.id,
            "email": p.user.email,
            "name": p.user.username,

            "plan_id": p.plan.id if p.plan else None,
            "plan_name": p.plan.name if p.plan else "Free",

            "amount": p.amount,
            "status": p.status,
            "provider": p.provider,
            "provider_payment_id": p.provider_payment_id,
            "provider_order_id": p.provider_order_id,

            "created_at": p.created_at,
            "expire_at": None  # removed expensive query
        })

    # ==========================================================
    # CREDITS (LIMITED)
    # ==========================================================
    credits_qs = CreditTransaction.objects.select_related(
        "user", "feature", "template"
    ).filter(user__is_staff=False).order_by("-created_at")[:50]

    credits_list = []

    for c in credits_qs:
        credits_list.append({
            "id": c.id,
            "user_id": c.user.id,
            "email": c.user.email,
            "name": c.user.username,

            "action": c.transaction_action,
            "amount": c.amount,
            "type": c.transaction_type,

            "feature_id": c.feature_id,
            "feature_name": c.feature.name if c.feature else None,

            "template_id": c.template_id,
            "template_name": c.template.name if c.template else None,

            "balance_before": c.balance_before,
            "balance_after": c.balance_after,

            "created_at": c.created_at,
            "created_at_formatted": c.created_at.strftime("%d %b %Y, %I:%M %p"),
        })

    # ==========================================================
    # GENERATIONS (AGGREGATED)
    # ==========================================================
    gen_stats = Generation.objects.aggregate(
        total=Count("id"),
        failed=Count("id", filter=Q(status="failed"))
    )

    total_generations = gen_stats["total"]
    failed_count = gen_stats["failed"]

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
    # TEMPLATES + MODELS
    # ==========================================================
    most_used_templates = Generation.objects.filter(
        template__isnull=False
    ).values(
        "template__id", "template__name"
    ).annotate(usage=Count("id")).order_by("-usage")[:10]

    model_usage = AIModel.objects.values(
        "model_name", "name", "total_usage_count", "total_credits_used"
    ).order_by("-total_usage_count")[:10]

    # ==========================================================
    # CREDITS + EARNINGS (AGGREGATED)
    # ==========================================================
    credit_stats = CreditTransaction.objects.aggregate(
        issued=Sum("amount", filter=Q(transaction_action="add")),
        used=Sum("amount", filter=Q(transaction_action="deduct"))
    )

    total_credits_issued = credit_stats["issued"] or 0
    total_credits_used = credit_stats["used"] or 0

    total_earnings = Payment.objects.filter(
        status="success"
    ).aggregate(total=Sum("amount"))["total"] or 0

    # ==========================================================
    # AI USAGE (SINGLE QUERY)
    # ==========================================================
    ai_stats = Generation.objects.aggregate(
        templates=Count("id", filter=Q(template__isnull=False)),
        features=Count("id", filter=Q(feature__isnull=False)),
        auto_video=Count("id", filter=Q(source_type="auto_video"))
    )

    ai_usage = ai_stats

    # ==========================================================
    # ALERTS (PERCENTAGE FIXED)
    # ==========================================================
    alerts = []

    failure_rate = (failed_count / total_generations * 100) if total_generations else 0

    if failure_rate > 20:
        alerts.append({
            "type": "error",
            "message": f"High generation failure rate: {round(failure_rate,2)}%"
        })

    if total_credits_used > total_credits_issued * 0.9:
        alerts.append({
            "type": "warning",
            "message": "Credits usage nearing limit"
        })

    if total_active_users < total_users * 0.3:
        alerts.append({
            "type": "warning",
            "message": "Low user activity detected"
        })

    # ==========================================================
    # RECENT
    # ==========================================================
    recent_transactions = credits_list[:10]
    recent_payments = payments_list[:10]

    # ==========================================================
    # ADMIN ACTIVITY (CASE INSENSITIVE FIX)
    # ==========================================================
    admin_activity_qs = CreditTransaction.objects.select_related("user").annotate(
        action_lower=Lower("transaction_action"),
        type_lower=Lower("transaction_type")
    ).filter(
        user__is_staff=False,
        action_lower__in=["add", "deduct"],
        type_lower__in=[
            "admin reward",
            "bonus",
            "admin penalty",
            "penalty",
            "reward"
        ]
    ).order_by("-created_at")[:20]

    admin_activity = []

    for c in admin_activity_qs:
        if c.action_lower == "add":
            action = "added"
            message = f"{c.amount} credits added to {c.user.username}"
        else:
            action = "deducted"
            message = f"{c.amount} credits deducted from {c.user.username}"

        admin_activity.append({
            "id": c.id,
            "type": action,
            "transaction_type": c.transaction_type,
            "message": message,
            "user_id": c.user.id,
            "email": c.user.email,
            "name": c.user.username,
            "amount": c.amount,
            "created_at": c.created_at,
            "created_at_formatted": c.created_at.strftime("%d %b %Y, %I:%M %p"),
        })

    # ==========================================================
    # FINAL RESPONSE (UNCHANGED STRUCTURE)
    # ==========================================================
    return {
        "users": {
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
        "kpis": {
            "total_users": total_users,
            "total_active_users": total_active_users,
            "total_staff_users": total_staff_users,
            "banned_users": banned_users,
            "total_subscriptions": total_subscriptions,
            "total_credits_issued": total_credits_issued,
            "total_credits_used": total_credits_used,
            "total_earnings": total_earnings
        },
        "ai_usage": ai_usage,
        "alerts": alerts,
        "recent": {
            "credits_transactions": recent_transactions,
            "payment_transactions": recent_payments
        },
        "admin_activity": admin_activity
    }