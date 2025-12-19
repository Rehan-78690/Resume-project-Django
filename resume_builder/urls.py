# resume_builder/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Our custom auth API
    path("api/auth/", include("accounts.urls")),

    # Resumes API
    path("api/", include("resumes.urls")),
    
    # Cover Letters API
    path("api/cover-letters/", include("cover_letters.urls")),

    # Social login endpoints (Google/Facebook)
    path("api/auth/social/", include("allauth.socialaccount.urls")),

    # API schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
