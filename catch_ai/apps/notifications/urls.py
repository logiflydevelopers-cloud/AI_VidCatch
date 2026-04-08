# notifications/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # User APIs
    path("banner/", views.get_active_banner),
    path("all/", views.get_active_notifications)
]

