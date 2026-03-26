from django.urls import path
from .views import purchase_plan

urlpatterns = [
    path("purchase-plan/", purchase_plan),
]