# notifications/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # User APIs
    path("slider/", views.get_slider_notifications, name="slider-notifications"),
    path("popup/", views.get_popup_notifications, name="popup-notifications")
]

