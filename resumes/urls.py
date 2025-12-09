from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'resumes', views.ResumeViewSet, basename='resume')
router.register(r'templates', views.TemplateViewSet, basename='template')

urlpatterns = [
    path('', include(router.urls)),
    
    # AI Endpoints
    path('ai/quick-resume/preview/', 
         views.QuickResumePreviewAPIView.as_view(), 
         name='ai-quick-resume-preview'),
    
    path('ai/quick-resume/confirm/', 
         views.QuickResumeConfirmAPIView.as_view(), 
         name='ai-quick-resume-confirm'),
    
    path('ai/sections/rewrite/', 
         views.SectionRewriteAPIView.as_view(), 
         name='ai-section-rewrite'),
    
    # Stats
    path('stats/', 
         views.ResumeStatsAPIView.as_view(), 
         name='resume-stats'),
]