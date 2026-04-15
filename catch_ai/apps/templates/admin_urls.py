from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template,
    get_ai_models,
    update_ai_model,
    get_templates
)

from apps.features.admin_views import (
    list_features,
    get_feature,
    update_feature
)

from apps.dashboard.views import dashboard

# ✅ UPDATED USER IMPORT
from apps.users.admin_views import delete_user, admin_user_detail

from apps.notifications.admin_views import (
    get_all_notifications,
    create_notification,
    update_notification,
    delete_notification
)

from apps.subscriptions.admin_views import plans, plan_detail


urlpatterns = [

    # ==========================
    # TEMPLATES
    # ==========================
    path("templates/", create_template),
    path("templates/list/", get_templates),
    path("templates/<str:template_id>/", update_template),
    path("templates/<str:template_id>/delete/", delete_template),

    # ==========================
    # AI MODELS
    # ==========================
    path("ai-models/", get_ai_models),
    path("ai-models/<str:model_id>/", update_ai_model),

    # ==========================
    # FEATURES (FIXED DUPLICATES)
    # ==========================
    path("features/", list_features),
    path("features/<str:feature_id>/", get_feature),
    path("features/<str:feature_id>/update/", update_feature),

    # ==========================
    # DASHBOARD
    # ==========================
    path("dashboard/", dashboard),

    # ==========================
    # USERS (🔥 UPDATED)
    # ==========================
    path("users/<str:user_id>/", admin_user_detail),  # ✅ GET + PATCH
    path("users/<str:user_id>/delete/", delete_user),

    # ==========================
    # NOTIFICATIONS
    # ==========================
    path("notifications/", get_all_notifications),
    path("notifications/create/", create_notification),
    path("notifications/<str:notif_id>/update/", update_notification),
    path("notifications/<str:notif_id>/delete/", delete_notification),

    # ==========================
    # PLANS
    # ==========================
    path("plans/", plans),
    path("plans/<str:plan_id>/", plan_detail),
]