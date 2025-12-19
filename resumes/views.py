import logging
from django.shortcuts import get_object_or_404
from django.conf import settings

from django.utils import timezone
from django.db import transaction
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse,OpenApiExample
from drf_spectacular.types import OpenApiTypes

from accounts.models import User
from .models import (
    Resume, PersonalInfo, WorkExperience, Education,
    SkillCategory, SkillItem, Strength, Hobby,
    CustomSection, CustomItem, ResumeWizardSession, Template
)
from .serializers import (
    ResumeListSerializer, ResumeDetailSerializer,
    ResumeCreateSerializer, ResumeUpdateSerializer,
    PersonalInfoSerializer, WorkExperienceSerializer,
    EducationSerializer, SkillCategorySerializer,
    StrengthSerializer, HobbySerializer,
    CustomSectionSerializer, QuickResumeInputSerializer,
    QuickResumeConfirmSerializer, SectionRewriteSerializer,
    ResumeWizardSessionSerializer, TemplateSerializer
)
from .permissions import IsOwnerOrAdmin
from .services.ai_service import AIResumeService
from .services.ai_service import AIResumeService
from .services.resume_service import ResumeService
from .services.pdf_service import PdfService
from .services.share_service import ShareService
from .models import ShareLink
from django.http import HttpResponse

logger = logging.getLogger(__name__)


@extend_schema(tags=['templates'])
class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing resume templates (READ-ONLY).
    All template creation/modification must be done via admin endpoints.
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Non-staff users can only see active templates."""
        if self.request.user.is_staff:
            return Template.objects.all()
        return Template.objects.filter(is_active=True)


class ResumeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing resumes.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """Return only non-deleted resumes for the current user."""
        return Resume.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True
        ).prefetch_related(
            'personal_info',
            'work_experiences',
            'educations',
            'skill_categories__items',
            'strengths',
            'hobbies',
            'custom_sections__items'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ResumeListSerializer
        elif self.action == 'create':
            return ResumeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ResumeUpdateSerializer
        return ResumeDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @extend_schema(
        responses=ResumeDetailSerializer,
        summary="Duplicate a resume"
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a resume with all its content."""
        resume = self.get_object()
        
        try:
            new_resume = ResumeService.duplicate_resume(
                resume,
                request.data.get('title')
            )
            serializer = self.get_serializer(new_resume)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to duplicate resume {pk}: {e}")
            return Response(
                {"detail": "Failed to duplicate resume"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Soft delete a resume",
        description="Marks resume as deleted but doesn't remove from database."
    )
    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        """Soft delete a resume."""
        resume = self.get_object()
        resume.soft_delete()
        return Response(
            {"detail": "Resume deleted successfully"},
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        summary="Export resume as JSON"
    )
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export resume as JSON."""
        resume = self.get_object()
        serializer = ResumeDetailSerializer(resume)
        return Response(serializer.data)

    @extend_schema(
        summary="Download resume as PDF",
        responses={
            200: OpenApiTypes.BINARY,
            503: OpenApiResponse(description="PDF provider not configured")
        }
    )
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate and download PDF."""
        resume = self.get_object()
        
        try:
            pdf_service = PdfService()
            if not pdf_service.provider and not settings.DEBUG:
                return Response(
                    {"detail": "PDF provider not configured"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
                
            pdf_content = pdf_service.generate_pdf(resume)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"resume-{resume.slug}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return Response(
                {"detail": "Failed to generate PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post', 'delete'])
    def share(self, request, pk=None):
        """Manage public share link."""
        resume = self.get_object()
        
        if request.method == 'DELETE':
            ShareService.revoke_link(request.user, ShareLink.ResourceType.RESUME, resume.id)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        # POST: Create/Get link
        link = ShareService.create_link(request.user, ShareLink.ResourceType.RESUME, resume.id)
        # Build full URL (e.g., frontend URL)
        # Assuming frontend is at localhost:3000/share/resume/<token> or similar
        # For API, we return the token and maybe the API public url
        
        return Response({
            "token": link.token,
            "url": f"/public/r/{link.token}/",
            "expires_at": link.expires_at,
            "is_active": link.is_active
        })
    
    @extend_schema(
        summary="Autosave resume",
        request=ResumeUpdateSerializer,
        description="Dedicated autosave endpoint - functionally identical to PATCH"
    )
    @action(detail=True, methods=['post'])
    def autosave(self, request, pk=None):
        """Dedicated autosave endpoint for frontend convenience."""
        resume = self.get_object()
        serializer = ResumeUpdateSerializer(
            resume,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            "success": True,
            "message": "Resume autosaved",
            "last_edited_at": resume.last_edited_at
        })
    
    @extend_schema(
        summary="Create resume snapshot",
        description="Create a version snapshot of the current resume state"
    )
    @action(detail=True, methods=['post'])
    def snapshot(self, request, pk=None):
        """Create a snapshot of current resume state."""
        from resumes.services.version_service import VersionService
        from resumes.models import ResumeVersion
        
        resume = self.get_object()
        version = VersionService.create_snapshot(resume, request.user)
        
        return Response({
            "id": str(version.id),
            "version_number": version.version_number,
            "created_at": version.created_at
        }, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="List resume versions",
        description="Get version history for this resume"
    )
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """List all versions for this resume."""
        from resumes.models import ResumeVersion
        
        resume = self.get_object()
        versions = ResumeVersion.objects.filter(resume=resume)
        
        data = [{
            "id": str(v.id),
            "version_number": v.version_number,
            "created_at": v.created_at,
            "created_by": v.created_by.email if v.created_by else None
        } for v in versions]
        
        return Response(data)
    
    @extend_schema(
        summary="Restore resume to version",
        description="Restore resume to a previous version snapshot"
    )
    @action(detail=True, methods=['post'], url_path='versions/(?P<version_id>[^/.]+)/restore')
    def restore_version(self, request, pk=None, version_id=None):
        """Restore resume to a specific version."""
        from resumes.services.version_service import VersionService
        
        resume = self.get_object()
        
        try:
            VersionService.restore_version(resume, version_id, request.user)
            resume.refresh_from_db()
            
            serializer = ResumeDetailSerializer(resume)
            return Response({
                "message": "Resume restored successfully",
                "resume": serializer.data
            })
        except Exception as e:
            logger.error(f"Failed to restore version: {e}")
            return Response(
                {"detail": "Failed to restore version"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Override destroy to soft delete."""
        resume = self.get_object()
        resume.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuickResumePreviewAPIView(APIView):
    """
    Generate an AI draft resume (preview, not saved).
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_generation'
    
    @extend_schema(
        request=QuickResumeInputSerializer,
        summary="Generate AI draft resume"
    )
    def post(self, request):
        serializer = QuickResumeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        input_payload = serializer.validated_data
        
        # Prepare user data for AI
        user_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'photo_url': user.avatar_url or ''
        }
        
        # Handle social photo import
        if input_payload.get('use_social_photo'):
            photo_source = input_payload.get('photo_source')
            if photo_source:
                try:
                    # Get social account photo
                    from allauth.socialaccount.models import SocialAccount
                    social_account = SocialAccount.objects.get(
                        user=user,
                        provider=photo_source
                    )
                    if photo_source == 'google':
                        user_data['photo_url'] = social_account.extra_data.get('picture', '')
                    elif photo_source == 'facebook':
                        picture_data = social_account.extra_data.get('picture', {}).get('data', {})
                        user_data['photo_url'] = picture_data.get('url', '')
                except Exception as e:
                    logger.warning(f"Failed to get social photo: {e}")
        
        # Generate AI draft
        try:
            ai_service = AIResumeService()
            draft_payload = ai_service.generate_resume_from_input(
                user=request.user,
                user_input=input_payload,
                user_data=user_data
            )
            
            # Add metadata
            draft_payload['meta'] = {
                'generated_at': timezone.now().isoformat(),
                'model': ai_service.model,
                'prompt_hash': hash(str(input_payload))
            }
            
        except Exception as e:
            logger.error(f"AI generation failed for user {user.email}: {e}")
            return Response(
                {
                    "detail": "Failed to generate resume. Please try again.",
                    "error": str(e) if settings.DEBUG else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create wizard session
        wizard = ResumeWizardSessionSerializer.create_session(
            user=user,
            input_payload=input_payload,
            draft_payload=draft_payload
        )
        
        return Response({
            "wizard_id": str(wizard.id),
            "draft_resume": draft_payload,
            "expires_at": wizard.expires_at
        })


class QuickResumeConfirmAPIView(APIView):
    """
    Confirm and save AI-generated resume.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request=QuickResumeConfirmSerializer,
        summary="Save AI-generated resume"
    )
    def post(self, request):
        serializer = QuickResumeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wizard_id = serializer.validated_data['wizard_id']
        template = serializer.validated_data['template_id']  # This is now a Template object
        title = serializer.validated_data['title']
        
        # Get wizard session
        wizard = get_object_or_404(
            ResumeWizardSession,
            id=wizard_id,
            user=request.user
        )
        
        # Validate wizard
        if wizard.consumed:
            return Response(
                {"detail": "This draft has already been used"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if wizard.is_expired():
            return Response(
                {"detail": "This draft has expired. Please generate a new one."},
                status=status.HTTP_410_GONE
            )
        
        # Create resume from draft
        try:
            resume = ResumeService.create_resume_from_draft(
                user=request.user,
                template_id=template.id,  # Pass ID string to service
                title=title,
                draft_payload=wizard.draft_payload
            )
            
            # Mark wizard as consumed
            wizard.mark_consumed()
            
            # Log success
            logger.info(f"Resume created from wizard {wizard_id} for user {request.user.email}")
            
            return Response({
                "resume_id": str(resume.id),
                "redirect_url": f"/dashboard/resumes/{resume.id}/edit/",
                "slug": resume.slug
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create resume from wizard {wizard_id}: {e}")
            return Response(
                {"detail": "Failed to save resume. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SectionRewriteAPIView(APIView):
    """
    AI-powered section rewriting.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request=SectionRewriteSerializer,
        summary="Rewrite a resume section with AI"
    )
    def post(self, request):
        serializer = SectionRewriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        resume_id = serializer.validated_data['resume_id']
        section_type = serializer.validated_data['section_type']
        item_id = serializer.validated_data.get('item_id')
        prompt = serializer.validated_data['prompt']
        tone = serializer.validated_data['tone']
        
        # Get resume and verify ownership
        resume = get_object_or_404(
            Resume,
            id=resume_id,
            user=request.user
        )
        
        ai_service = AIResumeService()
        
        try:
            if section_type == 'work_experience' and item_id:
                # Rewrite specific work experience
                work_exp = get_object_or_404(
                    WorkExperience,
                    id=item_id,
                    resume=resume
                )
                
                original_text = "\n".join(work_exp.bullets) if work_exp.bullets else work_exp.description
                rewritten = ai_service.rewrite_section(request.user, original_text, prompt, tone)
                
                # Update
                work_exp.bullets = [rewritten] if rewritten else []
                work_exp.save()
                
                return Response({
                    "success": True,
                    "rewritten_text": rewritten,
                    "item_id": str(item_id)
                })
                
            elif section_type == 'summary':
                # Rewrite personal summary
                if not hasattr(resume, 'personal_info'):
                    return Response(
                        {"detail": "Personal info not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                original_text = resume.personal_info.summary
                rewritten = ai_service.rewrite_section(request.user, original_text, prompt, tone)
                
                resume.personal_info.summary = rewritten
                resume.personal_info.save()
                
                return Response({
                    "success": True,
                    "rewritten_text": rewritten
                })
                
            else:
                return Response(
                    {"detail": "Section type not supported yet"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Section rewrite failed: {e}")
            return Response(
                {"detail": "Failed to rewrite section"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeStatsAPIView(APIView):
    """
    Get resume statistics for dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get resume statistics"
    )
    def get(self, request):
        stats = {
            "total": Resume.objects.filter(
                user=request.user,
                deleted_at__isnull=True
            ).count(),
            "draft": Resume.objects.filter(
                user=request.user,
                status='draft',
                deleted_at__isnull=True
            ).count(),
            "published": Resume.objects.filter(
                user=request.user,
                status='published',
                deleted_at__isnull=True
            ).count(),
            "ai_generated": Resume.objects.filter(
                user=request.user,
                is_ai_generated=True,
                deleted_at__isnull=True
            ).count(),
            "recent": Resume.objects.filter(
                user=request.user,
                deleted_at__isnull=True
            ).order_by('-updated_at')[:5].values('id', 'title', 'updated_at')
        }
        
        return Response(stats)