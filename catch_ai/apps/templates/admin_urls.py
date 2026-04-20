from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template,
    get_ai_models,
    update_ai_model,
    get_templates,
    auto_video_config
)

from apps.features.admin_views import (
    list_features,
    get_feature,
    update_feature
)

from apps.dashboard.views import dashboard

from apps.users.admin_views import (
    delete_user,
    admin_user_detail
)

from apps.notifications.admin_views import (
    notifications, notification_detail
)

from apps.subscriptions.admin_views import plans, plan_detail
from apps.plan_slider.admin_views import plan_slides, plan_slide_detail


urlpatterns = [

    # ==========================
    # TEMPLATES
    # ==========================
    path("templates/", create_template),
    path("templates/list/", get_templates),
    path("auto-video-config/", auto_video_config),
    path("templates/<str:template_id>/", update_template),
    path("templates/<str:template_id>/delete/", delete_template),  
    path("auto-video-config/<str:config_id>/", auto_video_config),

    # ==========================
    # AI MODELS
    # ==========================
    path("ai-models/", get_ai_models),
    path("ai-models/<str:model_id>/", update_ai_model),

    # ==========================
    # FEATURES
    # ==========================
    path("features/", list_features),
    path("features/<str:feature_id>/", get_feature),
    path("features/<str:feature_id>/update/", update_feature),

    # ==========================
    # DASHBOARD
    # ==========================
    path("dashboard/", dashboard),

    # ==========================
    # USERS
    # ==========================
    path("users/<str:user_id>/", admin_user_detail),      
    path("users/<str:user_id>/delete/", delete_user),

    # ==========================
    # NOTIFICATIONS
    # ==========================
    path("notifications/", notifications),
    path("notifications/<str:notif_id>/", notification_detail),

    # ==========================
    # PLANS
    # ==========================
    path("plans/", plans),
    path("plans/<str:plan_id>/", plan_detail),

    path("plan-slides/", plan_slides),
    path("<str:slide_id>/", plan_slide_detail),
]