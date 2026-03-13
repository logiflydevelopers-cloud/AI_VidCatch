from django.urls import path
from .admin_views import (
    create_template,
    update_template,
    delete_template
)

urlpatterns = [
    path("", create_template),
    path("<str:template_id>/", update_template),
    path("<str:template_id>/delete/", delete_template),
]