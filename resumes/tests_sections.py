"""
Tests for section-specific endpoints.
Tests CRUD operations, ownership enforcement, and staff access.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from resumes.models import Template, Resume, WorkExperience, PersonalInfo, SkillCategory, SkillItem
import uuid

User = get_user_model()


class SectionEndpointTests(TestCase):
    """Test section endpoints CRUD and security."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.other_user = User.objects.create_user(email='other@example.com', password='password')
        self.staff = User.objects.create_superuser(email='staff@example.com', password='password')
        
        # Create template
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)
        
        # Create resume for user
        self.resume = Resume.objects.create(
            user=self.user,
            title='My Resume',
            template_id='classic-1'
        )
        
        # Create resume for other user
        self.other_resume = Resume.objects.create(
            user=self.other_user,
            title='Other Resume',
            template_id='classic-1'
        )
    
    def test_owner_can_create_work_experience(self):
        """Owner can create work experience via nested endpoint."""
        self.client.force_authenticate(user=self.user)
        data = {
            'position_title': 'Software Engineer',
            'company_name': 'Tech Co',
            'start_date': '2020-01',
            'end_date': '2023-01',
            'is_current': False,
            'description': 'Built things',
            'bullets': ['Achievement 1', 'Achievement 2'],
            'order': 0
        }
        url = reverse('resume-work-experience-list', args=[self.resume.id])
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['position_title'], 'Software Engineer')
        
        # Verify it's linked to resume
        exp = WorkExperience.objects.get(id=response.data['id'])
        self.assertEqual(exp.resume, self.resume)
    
    def test_other_user_cannot_access_work_experience(self):
        """Other user cannot access or create sections under someone else's resume."""
        self.client.force_authenticate(user=self.other_user)
        
        # Try to list
        url = reverse('resume-work-experience-list', args=[self.resume.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to create
        data = {'position_title': 'Hacker', 'company_name': 'Evil Corp', 'start_date': '2020'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_cannot_create_section_under_other_user_resume(self):
        """Explicitly test cannot create under other user's resume."""
        self.client.force_authenticate(user=self.user)
        data = {'position_title': 'Test', 'company_name': 'Test', 'start_date': '2020'}
        url = reverse('resume-work-experience-list', args=[self.other_resume.id])
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_staff_can_access_any_resume_sections(self):
        """Staff users can access sections from any resume."""
        self.client.force_authenticate(user=self.staff)
        
        # Should be able to list other user's work experiences
        url = reverse('resume-work-experience-list', args=[self.resume.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be able to create
        data = {
            'position_title': 'Admin Created',
            'company_name': 'Admin Co',
            'start_date': '2020'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class PersonalInfoSingletonTests(TestCase):
    """Test PersonalInfo singleton endpoint behavior."""
    
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
    
    def test_personal_info_singleton_patch_creates_or_updates(self):
        """PATCH creates PersonalInfo if missing, or updates if exists."""
        self.client.force_authenticate(user=self.user)
        url = reverse('resume-personal-info', args=[self.resume.id])
        
        # First PATCH (no PersonalInfo exists yet)
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'John')
        
        # Verify created
        self.assertTrue(PersonalInfo.objects.filter(resume=self.resume).exists())
        
        # Second PATCH (PersonalInfo exists, should update)
        data = {'first_name': 'Jane'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Jane')
        self.assertEqual(response.data['last_name'], 'Doe')  # Unchanged
        
        # Still only one PersonalInfo
        self.assertEqual(PersonalInfo.objects.filter(resume=self.resume).count(), 1)
