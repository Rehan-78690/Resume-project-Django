from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from resumes.models import Template, Resume, ResumeVersion
from cover_letters.models import CoverLetter, CoverLetterTemplate

User = get_user_model()


class TemplatePermissionTests(TestCase):
    """Test template permission restructuring."""
    
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.template = Template.objects.create(
            id='test-1',
            name='Test Template',
            is_active=True
        )
        self.inactive_template = Template.objects.create(
            id='test-2',
            name='Inactive Template',
            is_active=False
        )
    
    def test_regular_user_can_list_active_templates(self):
        """Regular users can GET active templates."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only active template
    
    def test_admin_can_see_all_templates(self):
        """Admin users can see all templates including inactive."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_regular_user_cannot_create_template(self):
        """Regular users cannot POST to /api/templates/."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/templates/', {'name': 'New Template'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_admin_can_create_via_admin_endpoint(self):
        """Admin can create templates via /api/admin/templates/."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/admin/templates/', {
            'id': 'new-template',
            'name': 'New Template'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class CoverLetterTemplateTests(TestCase):
    """Test cover letter template functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.template = CoverLetterTemplate.objects.create(
            id='cl-test-1',
            name='Professional Template',
            is_active=True
        )
    
    def test_user_can_list_cover_letter_templates(self):
        """Users can list active cover letter templates."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/cover-letters/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
    
    def test_user_cannot_create_template(self):
        """Regular users cannot create cover letter templates."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/cover-letters/templates/', {'name': 'New'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_admin_can_manage_templates(self):
        """Admin can CRUD cover letter templates."""
        self.client.force_authenticate(user=self.admin)
        
        # Create
        response = self.client.post('/api/admin/cover-letter-templates/', {
            'id': 'new-cl-template',
            'name': 'New CL Template'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Toggle active
        response = self.client.post(f'/api/admin/cover-letter-templates/{self.template.id}/toggle_active/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_cover_letter_links_to_template(self):
        """Cover letters can be linked to templates."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/cover-letters/', {
            'title': 'My CL',
            'template_id': self.template.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['template'], self.template.id)


class ResumeVersionHistoryTests(TestCase):
    """Test resume version history."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        template = Template.objects.create(id='test-tpl', name='Test')
        self.resume = Resume.objects.create(
            user=self.user,
            title='My Resume',
            template=template
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_snapshot(self):
        """Can create resume snapshot."""
        response = self.client.post(f'/api/resumes/{self.resume.id}/snapshot/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['version_number'], 1)
        
        # Check version was created
        self.assertTrue(
            ResumeVersion.objects.filter(resume=self.resume).exists()
        )
    
    def test_list_versions(self):
        """Can list resume versions."""
        # Create a snapshot first
        self.client.post(f'/api/resumes/{self.resume.id}/snapshot/')
        
        response = self.client.get(f'/api/resumes/{self.resume.id}/versions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_version_number_increments(self):
        """Version numbers increment correctly."""
        self.client.post(f'/api/resumes/{self.resume.id}/snapshot/')
        response = self.client.post(f'/api/resumes/{self.resume.id}/snapshot/')
        
        self.assertEqual(response.data['version_number'], 2)
    
    def test_restore_version(self):
        """Can restore resume to previous version."""
        # Create snapshot
        self.resume.title = "Original Title"
        self.resume.save()
        response = self.client.post(f'/api/resumes/{self.resume.id}/snapshot/')
        version_id = response.data['id']
        
        # Change resume
        self.resume.title = "Modified Title"
        self.resume.save()
        
        # Restore
        response = self.client.post(
            f'/api/resumes/{self.resume.id}/versions/{version_id}/restore/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify restored
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.title, "Original Title")


class CoverLetterPDFTests(TestCase):
    """Test cover letter PDF generation."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        template = CoverLetterTemplate.objects.create(
            id='cl-tpl-1',
            name='Test Template'
        )
        self.cover_letter = CoverLetter.objects.create(
            user=self.user,
            title='My CL',
            template=template,
            body='Test body'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_pdf_endpoint_exists(self):
        """PDF endpoint is accessible."""
        response = self.client.get(f'/api/cover-letters/{self.cover_letter.id}/pdf/')
        # Should return PDF (200) or 503 if no provider
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])
    
    def test_pdf_returns_pdf_content_type(self):
        """PDF endpoint returns correct content type."""
        response = self.client.get(f'/api/cover-letters/{self.cover_letter.id}/pdf/')
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response['Content-Type'], 'application/pdf')
