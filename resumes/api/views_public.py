from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from resumes.models import Resume, ShareLink
from cover_letters.models import CoverLetter
from resumes.serializers_public import ResumePublicSerializer
from cover_letters.serializers_public import CoverLetterPublicSerializer
from resumes.services.share_service import ShareService

class PublicResumeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        # Get and validate share link
        link = ShareService.get_public_resource(token, ShareLink.ResourceType.RESUME)
        if not link:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Check link expiry
        if link.expires_at and link.expires_at <= timezone.now():
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Get resume and check soft-delete
        try:
            resume = Resume.objects.get(id=link.resource_id, deleted_at__isnull=True)
        except Resume.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Serialize with public serializer (no sensitive fields)
        serializer = ResumePublicSerializer(resume)
        return Response(serializer.data)

class PublicCoverLetterView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        # Get and validate share link
        link = ShareService.get_public_resource(token, ShareLink.ResourceType.COVER_LETTER)
        if not link:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Check link expiry
        if link.expires_at and link.expires_at <= timezone.now():
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Get cover letter and check soft-delete
        try:
            cl = CoverLetter.objects.get(id=link.resource_id, deleted_at__isnull=True)
        except CoverLetter.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Serialize with public serializer (no sensitive fields)
        serializer = CoverLetterPublicSerializer(cl)
        return Response(serializer.data)
