from django.urls import path
from .views import sync_plans_api, sync_plans_admin, get_all_plans

urlpatterns = [
    path("sync-plans/", sync_plans_api),
    path("admin/sync-plans/", sync_plans_admin),
    path("plans/", get_all_plans),
]