from django.urls import path
from .views import signup, login, me, google_login, forgot_password, reset_password, credit_history

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("login/", login, name="login"),
    path("me/", me, name="me"),
    path("google-signin/", google_login, name="google_login"),
    path("forgot-password/", forgot_password),
    path("reset-password/", reset_password),
    path('credit-history/', credit_history),
]