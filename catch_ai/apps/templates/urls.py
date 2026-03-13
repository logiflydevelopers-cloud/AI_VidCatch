from django.urls import path
from .views import list_templates, get_template

urlpatterns = [
    path("", list_templates),
    path("<str:template_id>/", get_template),
]