"""
URL configuration for catch_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

def home(request):
    return JsonResponse({"status": "API running"})

urlpatterns = [
    path("", home),

    # Auth
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),

    # Django Admin
    path("admin/", admin.site.urls),

    # User APIs
    path("api/users/", include("apps.users.urls")),
    path("api/templates/", include("apps.templates.urls")),
    path("api/generations/", include("apps.generations.urls")),
    path("api/features/", include("apps.features.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/notifications/", include("apps.notifications.urls")),

    # Admin APIs (Separated properly)
    path("api/admin/", include("apps.templates.admin_urls"))
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)