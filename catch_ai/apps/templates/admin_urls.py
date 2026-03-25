from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template,
    get_ai_models,
    update_ai_model,
    get_templates
)

urlpatterns = [
    path("templates/", create_template),
    path("templates/list/", get_templates, name="get_templates"),
    path("ai-models/", get_ai_models),
    path("templates/<str:template_id>/", update_template),
    path("templates/<str:template_id>/delete/", delete_template),
    path("ai-models/<str:model_id>/", update_ai_model),
]