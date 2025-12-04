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
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    DeactivateAccountView,
    BasicProfileView, 
    SocialImportSourcesView,
)


app_name = "accounts"

urlpatterns = [
    # Registration (2-step)
    path("register/", RegisterView.as_view(), name="auth_register"),

    # login / tokens / profile / logout
    path("login/", LoginView.as_view(), name="auth_login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth_refresh"),
    path("me/", MeView.as_view(), name="auth_me"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),

    # password management
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth_forgot_password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth_reset_password"),
    path("change-password/", ChangePasswordView.as_view(), name="auth_change_password"),

    # account management
    path("deactivate/", DeactivateAccountView.as_view(), name="auth_deactivate"),

    # social logins (placeholders)
    path("google/", GoogleLoginView.as_view(), name="auth_google"),
    path("facebook/", FacebookLoginView.as_view(), name="auth_facebook"),
    path("profile/basic/", BasicProfileView.as_view(), name="profile_basic"),
    path("profile/import-sources/", SocialImportSourcesView.as_view(), name="import_sources"),
]
