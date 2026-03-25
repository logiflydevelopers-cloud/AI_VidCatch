from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template,
    # upload_template_cover,
    # upload_template_preview,
    get_ai_models,
    update_ai_model
)

urlpatterns = [
    path("templates/", create_template),
    path("ai-models/", get_ai_models),
    path("templates/<str:template_id>/", update_template),
    path("templates/<str:template_id>/delete/", delete_template),
    # path("<str:template_id>/upload/template_cover/", upload_template_cover),
    # path("<str:template_id>/upload/template_preview/", upload_template_preview),
    path("ai-models/<str:model_id>/", update_ai_model),
]