from django.urls import path
from .views import list_features, get_feature


urlpatterns = [
    path("features/", list_features, name="list-features"),
    path("features/<str:feature_id>/", get_feature, name="get-feature"),
]