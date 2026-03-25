from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template,
    # upload_template_cover,
    # upload_template_preview
)

urlpatterns = [
    path("", create_template),
    path("<str:template_id>/", update_template),
    path("<str:template_id>/delete/", delete_template),
    # path("<str:template_id>/upload/template_cover/", upload_template_cover),
    # path("<str:template_id>/upload/template_preview/", upload_template_preview),
]