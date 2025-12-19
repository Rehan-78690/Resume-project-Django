from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from resumes.permissions import IsOwnerOrAdmin
from .models import CoverLetter, CoverLetterTemplate
from .serializers import CoverLetterSerializer, CoverLetterTemplateSerializer
from resumes.services.share_service import ShareService
from resumes.models import ShareLink
import logging

logger = logging.getLogger(__name__)


@extend_schema(tags=['cover-letter-templates'])
class CoverLetterTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing cover letter templates (READ-ONLY).
    All template creation/modification must be done via admin endpoints.
    """
    queryset = CoverLetterTemplate.objects.all()
    serializer_class = CoverLetterTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Non-staff users can only see active templates."""
        if self.request.user.is_staff:
            return CoverLetterTemplate.objects.all()
        return CoverLetterTemplate.objects.filter(is_active=True)


@extend_schema(tags=['cover-letters'])
class CoverLetterViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = CoverLetterSerializer
    
    def get_queryset(self):
        return CoverLetter.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        cl = self.get_object()
        new_cl = CoverLetter.objects.create(
            user=request.user,
            linked_resume=cl.linked_resume,
            title=f"{cl.title} (Copy)",
            company_name=cl.company_name,
            job_title=cl.job_title,
            job_description=cl.job_description,
            body=cl.body,
            status=cl.status
        )
        return Response(CoverLetterSerializer(new_cl).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        cl = self.get_object()
        cl.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'])
    def share(self, request, pk=None):
        cl = self.get_object()
        if request.method == 'DELETE':
            ShareService.revoke_link(request.user, ShareLink.ResourceType.COVER_LETTER, cl.id)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        link = ShareService.create_link(request.user, ShareLink.ResourceType.COVER_LETTER, cl.id)
        return Response({
            "token": link.token,
            "url": f"/public/c/{link.token}/",
            "expires_at": link.expires_at
        })
    
    @extend_schema(
        summary="Download cover letter as PDF",
        description="Generate and download PDF version of cover letter"
    )
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate and download PDF."""
        from resumes.services.pdf_service import PdfService
        from django.http import HttpResponse
        from django.conf import settings
        
        cl = self.get_object()
        
        try:
            pdf_service = PdfService()
            if not pdf_service.provider and not settings.DEBUG:
                return Response(
                    {"detail": "PDF provider not configured"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
                
            pdf_content = pdf_service.generate_cover_letter_pdf(cl)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"cover-letter-{cl.id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            logger.error(f"CL PDF generation failed: {e}")
            return Response(
                {"detail": "Failed to generate PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        cl = self.get_object()
        cl.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
