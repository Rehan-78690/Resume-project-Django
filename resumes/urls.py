from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TemplateViewSet, ResumeViewSet,
    QuickResumePreviewAPIView, QuickResumeConfirmAPIView,
    SectionRewriteAPIView, ResumeStatsAPIView
)
from .views_sections import (
    PersonalInfoViewSet, WorkExperienceViewSet, EducationViewSet,
    StrengthViewSet, HobbyViewSet, SkillCategoryViewSet, SkillItemViewSet,
    CustomSectionViewSet, CustomItemViewSet
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
    
    # Section-specific endpoints (scoped to resume)
    path('resumes/<uuid:resume_id>/personal-info/', PersonalInfoViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update'
    }), name='resume-personal-info'),
    
    path('resumes/<uuid:resume_id>/work-experiences/', WorkExperienceViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-work-experience-list'),
    path('resumes/<uuid:resume_id>/work-experiences/<uuid:pk>/', WorkExperienceViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-work-experience-detail'),
    
    path('resumes/<uuid:resume_id>/educations/', EducationViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-education-list'),
    path('resumes/<uuid:resume_id>/educations/<uuid:pk>/', EducationViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-education-detail'),
    
    path('resumes/<uuid:resume_id>/strengths/', StrengthViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-strength-list'),
    path('resumes/<uuid:resume_id>/strengths/<uuid:pk>/', StrengthViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-strength-detail'),
    
    path('resumes/<uuid:resume_id>/hobbies/', HobbyViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-hobby-list'),
    path('resumes/<uuid:resume_id>/hobbies/<uuid:pk>/', HobbyViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-hobby-detail'),
    
    path('resumes/<uuid:resume_id>/skill-categories/', SkillCategoryViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-skill-category-list'),
    path('resumes/<uuid:resume_id>/skill-categories/<uuid:pk>/', SkillCategoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-skill-category-detail'),
    
    path('resumes/<uuid:resume_id>/skill-categories/<uuid:category_id>/items/', SkillItemViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-skill-item-list'),
    path('resumes/<uuid:resume_id>/skill-categories/<uuid:category_id>/items/<uuid:pk>/', SkillItemViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-skill-item-detail'),
    
    path('resumes/<uuid:resume_id>/custom-sections/', CustomSectionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-custom-section-list'),
    path('resumes/<uuid:resume_id>/custom-sections/<uuid:pk>/', CustomSectionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-custom-section-detail'),
    
    path('resumes/<uuid:resume_id>/custom-sections/<uuid:section_id>/items/', CustomItemViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='resume-custom-item-list'),
    path('resumes/<uuid:resume_id>/custom-sections/<uuid:section_id>/items/<uuid:pk>/', CustomItemViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='resume-custom-item-detail'),
    
    # Public share links
    path('public/r/<str:token>/', PublicResumeView.as_view(), name='public-resume'),
    path('public/c/<str:token>/', PublicCoverLetterView.as_view(), name='public-cover-letter'),
    
    # Admin APIs
    path('admin/', include(admin_router.urls)),
]