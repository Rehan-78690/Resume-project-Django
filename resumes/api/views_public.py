from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from resumes.models import Resume, ShareLink
from cover_letters.models import CoverLetter
from resumes.serializers import ResumeDetailSerializer
from cover_letters.serializers import CoverLetterSerializer
from resumes.services.share_service import ShareService

class PublicResumeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        link = ShareService.get_public_resource(token, ShareLink.ResourceType.RESUME)
        if not link:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        resume = get_object_or_404(Resume, id=link.resource_id)
        
        # Sanitize? Using standard serializer for now, check fields
        serializer = ResumeDetailSerializer(resume)
        data = serializer.data
        
        # Remove internal fields
        data.pop('user', None)
        data.pop('ai_prompt', None)
        data.pop('status', None) # Maybe?
        
        return Response(data)

class PublicCoverLetterView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        link = ShareService.get_public_resource(token, ShareLink.ResourceType.COVER_LETTER)
        if not link:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        cl = get_object_or_404(CoverLetter, id=link.resource_id)
        
        serializer = CoverLetterSerializer(cl)
        data = serializer.data
        data.pop('user', None)
        
        return Response(data)
