from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template,
    get_ai_models,
    update_ai_model,
    get_templates
)
from apps.features.admin_views import list_features, get_feature, update_feature
from apps.dashboard.views import dashboard
from apps.users.admin_views import delete_user

urlpatterns = [
    path("templates/", create_template),
    path("templates/list/", get_templates, name="get_templates"),
    path("ai-models/", get_ai_models),
    path("features/", list_features),
    path("templates/<str:template_id>/", update_template),
    path("templates/<str:template_id>/delete/", delete_template),
    path("ai-models/<str:model_id>/", update_ai_model),
    path("features/<str:feature_id>/", get_feature),
    path("features/<str:feature_id>/update/", update_feature),
    path("dashboard/", dashboard),
    path("users/<str:user_id>/", delete_user),
]
