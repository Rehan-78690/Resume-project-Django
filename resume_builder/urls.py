# resume_builder/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Our custom auth API
    path("api/auth/", include("accounts.urls")),



    # Registration (sign up)
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),

    # Social login endpoints (Google/Facebook)
    path("api/auth/social/", include("allauth.socialaccount.urls")),

    # We’ll add: path("api/accounts/", include("accounts.urls")) later
]
