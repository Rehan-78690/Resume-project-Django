"""
Tests for response contracts (ensuring correct serializers returned).
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from resumes.models import Template, Resume

User = get_user_model()


class ResumeResponseContractTests(TestCase):
    """Test that resume update endpoints return full detail payload."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My Resume',
            template_id='classic-1'
        )
    
    def test_resume_patch_returns_full_detail(self):
        """PATCH /api/resumes/{id}/ returns ResumeDetailSerializer payload."""
        self.client.force_authenticate(user=self.user)
        url = reverse('resume-detail', args=[self.resume.id])
        
        data = {'title': 'Updated Title'}
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have full detail fields
        self.assertIn('template', response.data)
        self.assertIn('personal_info', response.data)
        self.assertIn('work_experiences', response.data)
        self.assertIn('educations', response.data)
        self.assertIn('skill_categories', response.data)
        self.assertIn('strengths', response.data)
        self.assertIn('hobbies', response.data)
        self.assertIn('custom_sections', response.data)
        
        # Template should be expanded object, not just ID
        self.assertIsInstance(response.data['template'], dict)
        self.assertEqual(response.data['template']['id'], 'classic-1')
    
    def test_resume_put_returns_full_detail(self):
        """PUT /api/resumes/{id}/ returns ResumeDetailSerializer payload."""
        self.client.force_authenticate(user=self.user)
        url = reverse('resume-detail', args=[self.resume.id])
        
        data = {
            'title': 'Fully Updated',
            'template_id': 'classic-1',
            'language': 'en',
            'target_role': 'Engineer'
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have full detail fields
        self.assertIn('template', response.data)
        self.assertIn('personal_info', response.data)
        self.assertIn('work_experiences', response.data)
        
        # Verify updated title
        self.assertEqual(response.data['title'], 'Fully Updated')
