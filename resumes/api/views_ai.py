from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema
from resumes.services.ai_service import AIResumeService
from resumes.serializers import (
    AISummarySerializer, AIBulletsSerializer,
    AIExperienceSerializer, AICoverLetterBaseSerializer,
    AICoverLetterFullSerializer
)
import logging

logger = logging.getLogger(__name__)

class BaseAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_generation'

    def get_service(self):
        return AIResumeService()

    def handle_ai_request(self, request, serializer_class, method_name):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = self.get_service()
        try:
            # Dynamically call the method on service
            # Arguments from serializer data + user
            result = getattr(service, method_name)(
                user=request.user,
                **serializer.validated_data
            )
            
            return Response({
                "result": result,
                "meta": {
                    "model": service.model
                }
            })
        except Exception as e:
            logger.error(f"AI Error in {method_name}: {e}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AISummaryView(BaseAIView):
    @extend_schema(request=AISummarySerializer, summary="Generate resume summary")
    def post(self, request):
        return self.handle_ai_request(request, AISummarySerializer, 'generate_summary')

class AIBulletsView(BaseAIView):
    @extend_schema(request=AIBulletsSerializer, summary="Generate bullet points")
    def post(self, request):
        return self.handle_ai_request(request, AIBulletsSerializer, 'generate_bullets')

class AIExperienceView(BaseAIView):
    @extend_schema(request=AIExperienceSerializer, summary="Generate experience description")
    def post(self, request):
        return self.handle_ai_request(request, AIExperienceSerializer, 'generate_experience')

class AICoverLetterBaseView(BaseAIView):
    @extend_schema(request=AICoverLetterBaseSerializer, summary="Generate cover letter body")
    def post(self, request):
        return self.handle_ai_request(request, AICoverLetterBaseSerializer, 'generate_cover_letter_base')

class AICoverLetterFullView(BaseAIView):
    @extend_schema(request=AICoverLetterFullSerializer, summary="Generate full cover letter")
    def post(self, request):
        # Full cover letter needs more complex handling to fetch resume data
        serializer = AICoverLetterFullSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from resumes.models import Resume
        from django.shortcuts import get_object_or_404
        
        resume_id = serializer.validated_data['resume_id']
        resume = get_object_or_404(Resume, id=resume_id, user=request.user)
        
        # Extract resume data for AI
        resume_data = {
            "name": f"{request.user.first_name} {request.user.last_name}",
            "summary": resume.personal_info.summary if hasattr(resume, 'personal_info') else "",
            "skills": [item.name for cat in resume.skill_categories.all() for item in cat.items.all()]
        }
        
        job_details = {
            "company": serializer.validated_data['company_name'],
            "title": serializer.validated_data['job_title'],
            "description": serializer.validated_data.get('job_description', '')
        }
        
        service = self.get_service()
        try:
            result = service.generate_cover_letter_full(
                user=request.user,
                resume_data=resume_data,
                job_details=job_details,
                tone=serializer.validated_data['tone']
            )
            return Response({
                "result": result,
                "meta": {"model": service.model}
            })
        except Exception as e:
            logger.error(f"AI Cover Letter Error: {e}")
            return Response({"detail": str(e)}, status=500)
