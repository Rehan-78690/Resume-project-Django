from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CoverLetterViewSet, CoverLetterTemplateViewSet

router = DefaultRouter()
router.register(r'templates', CoverLetterTemplateViewSet, basename='cover-letter-template')
router.register(r'', CoverLetterViewSet, basename='cover-letter')

urlpatterns = [
    path('', include(router.urls)),
]
