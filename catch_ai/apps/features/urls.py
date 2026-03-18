from django.urls import path
from .views import list_features

urlpatterns = [
    path("", list_features, name="list-features"),
]