"""
Tests for public endpoint security.
Tests soft-delete, expiry, and field sanitization.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from resumes.models import Template, Resume, ShareLink
from resumes.services.share_service import ShareService
from cover_letters.models import CoverLetter, CoverLetterTemplate

User = get_user_model()


class PublicEndpointSecurityTests(TestCase):
    """Test public endpoint security against deleted/expired resources and sensitive fields."""
    
    def setUp(self):
        self.client = APIClient()  # No auth for public endpoints
        self.user = User.objects.create_user(email='user@example.com', password='password')
        
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='Public Resume',
            template_id='classic-1',
            ai_prompt={'key': 'sensitive data'}
        )
    
    def test_public_resume_404_for_deleted(self):
        """Public GET returns 404 for soft-deleted resume even with valid token."""
        # Create share link first
        link = ShareService.create_link(self.user, ShareLink.ResourceType.RESUME, self.resume.id)
        token = link.token
        
        # Soft delete the resume
        self.resume.soft_delete()
        
        # Try to access via public link
        response = self.client.get(f'/api/public/r/{token}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_public_resume_404_for_expired_link(self):
        """Public GET returns 404 for expired link."""
        # Create share link with past expiry
        link = ShareService.create_link(self.user, ShareLink.ResourceType.RESUME, self.resume.id)
        link.expires_at = timezone.now() - timedelta(hours=1)
        link.save()
        
        response = self.client.get(f'/api/public/r/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_public_resume_no_sensitive_fields(self):
        """Public response contains no sensitive/internal fields."""
        link = ShareService.create_link(self.user, ShareLink.ResourceType.RESUME, self.resume.id)
        
        response = self.client.get(f'/api/public/r/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should NOT have sensitive fields
        self.assertNotIn('user', response.data)
        self.assertNotIn('ai_prompt', response.data)
        self.assertNotIn('ai_model', response.data)
        self.assertNotIn('status', response.data)
        self.assertNotIn('is_ai_generated', response.data)
        self.assertNotIn('deleted_at', response.data)
        
        # Should have safe fields
        self.assertIn('title', response.data)
        self.assertIn('template', response.data)
        self.assertIn('personal_info', response.data)
        self.assertIn('section_settings', response.data)
        
        # Verify nested objects don't have internal fields
        if response.data.get('work_experiences'):
            for exp in response.data['work_experiences']:
                self.assertNotIn('resume', exp)
                self.assertNotIn('user', exp)
        
        if response.data.get('skill_categories'):
            for cat in response.data['skill_categories']:
                self.assertNotIn('resume', cat)
                if cat.get('items'):
                    for item in cat['items']:
                        self.assertNotIn('category', item)
    
    def test_public_cover_letter_404_for_deleted(self):
        """Public GET returns 404 for soft-deleted cover letter."""
        # Create cover letter template
        if not CoverLetterTemplate.objects.filter(id='standard-1').exists():
            CoverLetterTemplate.objects.create(id='standard-1', name='Standard')
        
        cl = CoverLetter.objects.create(
            user=self.user,
            title='My CL',
            template_id='standard-1',
            body='Content'
        )
        
        # Create share link
        link = ShareService.create_link(self.user, ShareLink.ResourceType.COVER_LETTER, cl.id)
        
        # Soft delete
        cl.soft_delete()
        
        # Try to access
        response = self.client.get(f'/api/public/c/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
