from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Template, Resume, ResumeWizardSession
from django.utils import timezone
import uuid

User = get_user_model()

class TemplateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='password')
        
        # Templates are seeded by migration, but let's ensure we control the state
        # Or better, check if migration ran. "classic-1" should exist.
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)
            
        # Create an inactive template
        Template.objects.create(id='inactive-1', name='Inactive', is_active=False)

    def test_list_templates(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('template-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        if 'results' in response.data:
            data = response.data['results']
        else:
            data = response.data
            
        ids = [t['id'] for t in data]
        self.assertIn('classic-1', ids)
        self.assertNotIn('inactive-1', ids)

    def test_admin_create_template(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'id': 'new-1',
            'name': 'New Template',
            'is_active': True,
            'definition': {
                'schema_version': 1,
                'layout': {'type': 'single'},
                'style': {},
                'sections': {}
            }
        }
        response = self.client.post(reverse('admin-template-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check if ID in response matches what we sent
        created_id = response.data['id']
        self.assertEqual(created_id, 'new-1')
        self.assertTrue(Template.objects.filter(id='new-1').exists())

    def test_user_cannot_create_template(self):
        self.client.force_authenticate(user=self.user)
        data = {'id': 'hacker-1', 'name': 'Hacker'}
        response = self.client.post(reverse('template-list'), data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

class ResumeTemplateIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        # Ensure classic-1 exists
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)

    def test_create_resume_with_valid_template(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'My Resume',
            'template_id': 'classic-1',
            'target_role': 'Dev'
        }
        response = self.client.post(reverse('resume-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['template_id'], 'classic-1')
        
        
        resume = Resume.objects.get(id=response.data['id'])
        self.assertEqual(resume.template.id, 'classic-1')

    def test_get_resume_detail_includes_template(self):
        self.client.force_authenticate(user=self.user)
        resume = Resume.objects.create(
            user=self.user, 
            title='Detail Test', 
            template_id='classic-1'
        )
        response = self.client.get(reverse('resume-detail', args=[resume.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['template']['id'], 'classic-1')
        self.assertIn('preview_image_url', response.data['template'])

    def test_create_resume_with_invalid_template(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Bad Resume',
            'template_id': 'invalid-one'
        }
        response = self.client.post(reverse('resume-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('template_id', response.data)

class AIQuickResumeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        # Ensure classic-1 exists
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)
            
        # Create a wizard session
        self.wizard = ResumeWizardSession.objects.create(
            user=self.user,
            input_payload={"target_role": "dev"},
            draft_payload={
                "personal_info": {"first_name": "Test"},
                "work_experience": [],
                "education": [],
                "skill_categories": [],
                "strengths": [],
                "hobbies": [],
                "custom_sections": []
            },
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )

    def test_confirm_with_valid_template(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'wizard_id': self.wizard.id,
            'template_id': 'classic-1',
            'title': 'AI Resume'
        }
        response = self.client.post(reverse('ai-confirm'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resume_id = response.data['resume_id']
        resume = Resume.objects.get(id=resume_id)
        self.assertEqual(resume.template.id, 'classic-1')
        
    def test_confirm_with_invalid_template(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'wizard_id': self.wizard.id,
            'template_id': 'non-existent',
            'title': 'AI Resume'
        }
        response = self.client.post(reverse('ai-confirm'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class TemplateDefinitionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='password')
        if not Template.objects.filter(id='classic-1').exists():
            Template.objects.create(id='classic-1', name='Classic', is_active=True)

    def test_admin_create_template_with_definition(self):
        self.client.force_authenticate(user=self.admin)
        definition = {
            "schema_version": 1,
            "layout": {"type": "one_column"},
            "style": {"font": "Arial"},
            "sections": {}
        }
        data = {
            'id': 'modern-custom-def-1',
            'name': 'Modern Custom Def',
            'is_active': True,
            'definition': definition
        }
        response = self.client.post(reverse('admin-template-list'), data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Create failed: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['definition'], definition)
        
    def test_admin_cannot_create_invalid_definition(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'id': 'broken-1',
            'name': 'Broken',
            'is_active': True,
            'definition': {
                'schema_version': 1, 
                'layout': {} 
            } # Missing sections/style
        }
        response = self.client.post(reverse('admin-template-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required key', str(response.data))

    def test_user_update_section_settings(self):
        self.client.force_authenticate(user=self.user)
        resume = Resume.objects.create(user=self.user, title='Settings Test', template_id='classic-1')
        
        settings = {
            "work_experiences": {"visible": False}
        }
        response = self.client.patch(
            reverse('resume-detail', args=[resume.id]), 
            {'section_settings': settings},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'section_settings' in response.data:
             self.assertEqual(response.data['section_settings']['work_experiences']['visible'], False)
        
        resume.refresh_from_db()
        self.assertEqual(resume.section_settings['work_experiences']['visible'], False)
        
    def test_user_cannot_update_invalid_settings(self):
        self.client.force_authenticate(user=self.user)
        resume = Resume.objects.create(user=self.user, title='Settings Test', template_id='classic-1')
        
        # Invalid key
        response = self.client.patch(
            reverse('resume-detail', args=[resume.id]), 
            {'section_settings': {'invalid_section': {}}},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Invalid value type
        response = self.client.patch(
            reverse('resume-detail', args=[resume.id]), 
            {'section_settings': {'work_experiences': "not-dict"}},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validation_rejects_missing_schema_version(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'id': 'bad-ver', 'name': 'Bad', 'is_active': True,
            'definition': {
               'layout': {'type': 's'}, 'style': {}, 'sections': {}
            }
        }
        response = self.client.post(reverse('admin-template-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing schema_version', str(response.data))

    def test_validation_rejects_invalid_section_types(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'id': 'bad-sec', 'name': 'Bad', 'is_active': True,
            'definition': {
               'schema_version': 1,
               'layout': {'type': 's'}, 'style': {}, 
               'sections': {
                   'header': {'visible': "not-bool"}
               }
            }
        }
        response = self.client.post(reverse('admin-template-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('visible', str(response.data))
