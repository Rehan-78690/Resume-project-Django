from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TemplateViewSet, ResumeViewSet,
    QuickResumePreviewAPIView, QuickResumeConfirmAPIView,
    SectionRewriteAPIView, ResumeStatsAPIView
)
from .api.views_ai import (
    AISummaryView, AIBulletsView, AIExperienceView,
    AICoverLetterBaseView, AICoverLetterFullView
)
from .api.views_public import PublicResumeView, PublicCoverLetterView
from .api.admin_views import AdminUserViewSet, AdminTemplateViewSet, AdminAILogViewSet, AdminCoverLetterTemplateViewSet

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'resumes', ResumeViewSet, basename='resume')

# Admin router
admin_router = DefaultRouter()
admin_router.register(r'users', AdminUserViewSet, basename='admin-user')
admin_router.register(r'templates', AdminTemplateViewSet, basename='admin-template')
admin_router.register(r'cover-letter-templates', AdminCoverLetterTemplateViewSet, basename='admin-cover-letter-template')
admin_router.register(r'ai-logs', AdminAILogViewSet, basename='admin-ailog')

urlpatterns = [
    # Main routes
    path('', include(router.urls)),
    
    # AI Endpoints
    path('ai/preview/', QuickResumePreviewAPIView.as_view(), name='ai-preview'),
    path('ai/confirm/', QuickResumeConfirmAPIView.as_view(), name='ai-confirm'),
    path('ai/rewrite/', SectionRewriteAPIView.as_view(), name='ai-rewrite'),
    path('ai/summary/', AISummaryView.as_view(), name='ai-summary'),
    path('ai/bullets/', AIBulletsView.as_view(), name='ai-bullets'),
    path('ai/experience/', AIExperienceView.as_view(), name='ai-experience'),
    path('ai/cover-letter/base/', AICoverLetterBaseView.as_view(), name='ai-cover-letter-base'),
    path('ai/cover-letter/full/', AICoverLetterFullView.as_view(), name='ai-cover-letter-full'),
    
    # Stats
    path('stats/', ResumeStatsAPIView.as_view(), name='resume-stats'),
    
    # Public share links
    path('public/r/<str:token>/', PublicResumeView.as_view(), name='public-resume'),
    path('public/c/<str:token>/', PublicCoverLetterView.as_view(), name='public-cover-letter'),
    
    # Admin APIs
    path('admin/', include(admin_router.urls)),
]