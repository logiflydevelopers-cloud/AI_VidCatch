from django.urls import path
from .views import public_plan_slides

urlpatterns = [
    path("", public_plan_slides),
    
]