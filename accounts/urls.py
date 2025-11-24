# accounts/urls.py
from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    RefreshTokenView,
    MeView,
    LogoutView,
    GoogleLoginView,
    FacebookLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("login/", LoginView.as_view(), name="auth_login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth_refresh"),
    path("me/", MeView.as_view(), name="auth_me"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),

    # Social login placeholders
    path("google/", GoogleLoginView.as_view(), name="auth_google"),
    path("facebook/", FacebookLoginView.as_view(), name="auth_facebook"),
]
