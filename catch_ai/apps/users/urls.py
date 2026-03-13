from django.urls import path
from .views import signup, login, me, google_login

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("login/", login, name="login"),
    path("me/", me, name="me"),
    path("google-signin/", google_login, name="google_login"),
]