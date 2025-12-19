from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from cover_letters.models import CoverLetter
from resumes.models import Resume, Template, ShareLink
from ai_core.models import AIUsageLog

User = get_user_model()


class CoverLetterCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user1)
        
    def test_create_cover_letter(self):
        data = {
            'title': 'My Cover Letter',
            'company_name': 'Test Corp',
            'job_title': 'Developer',
            'body': 'Cover letter body'
        }
        response = self.client.post('/api/cover-letters/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CoverLetter.objects.count(), 1)
        
    def test_list_cover_letters_owner_only(self):
        CoverLetter.objects.create(
            user=self.user1,
            title='CL 1'
        )
        CoverLetter.objects.create(
            user=self.user2,
            title='CL 2'
        )
        response = self.client.get('/api/cover-letters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
    def test_other_user_cannot_access(self):
        cl = CoverLetter.objects.create(
            user=self.user2,
            title='CL 2'
        )
        response = self.client.get(f'/api/cover-letters/{cl.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_duplicate_cover_letter(self):
        cl = CoverLetter.objects.create(
            user=self.user1,
            title='Original',
            body='Test body'
        )
        response = self.client.post(f'/api/cover-letters/{cl.id}/duplicate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CoverLetter.objects.count(), 2)
        

class ShareLinkTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.template = Template.objects.create(
            id='test-template',
            name='Test Template'
        )
        self.resume = Resume.objects.create(
            user=self.user,
            title='Test Resume',
            template=self.template
        )
        self.client.force_authenticate(user=self.user)
        
    def test_create_share_link(self):
        response = self.client.post(f'/api/resumes/{self.resume.id}/share/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertTrue(ShareLink.objects.filter(resource_id=self.resume.id).exists())
        
    def test_revoke_share_link(self):
        # Create link first
        self.client.post(f'/api/resumes/{self.resume.id}/share/')
        # Revoke it
        response = self.client.delete(f'/api/resumes/{self.resume.id}/share/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        link = ShareLink.objects.filter(resource_id=self.resume.id, is_active=True).first()
        self.assertIsNone(link)
        
    def test_public_access_with_valid_token(self):
        response = self.client.post(f'/api/resumes/{self.resume.id}/share/')
        token = response.data['token']
        
        # Try public access without auth
        public_client = APIClient()
        response = public_client.get(f'/api/public/r/{token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_public_access_with_invalid_token(self):
        public_client = APIClient()
        response = public_client.get('/api/public/r/invalid-token/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        

class AdminAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            password='testpass123'
        )
        
    def test_non_admin_cannot_access(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_admin_can_list_users(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
        
    def test_admin_can_view_ai_logs(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/ai-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AILoggingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        
    def test_ai_log_creation(self):
        from ai_core.services import AILogService
        
        log = AILogService.log_usage(
            user=self.user,
            feature_type=AIUsageLog.FeatureType.SUMMARY,
            model_name='gpt-4',
            prompt='test prompt',
            tokens_in=100,
            tokens_out=50,
            success=True
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.feature_type, AIUsageLog.FeatureType.SUMMARY)
        self.assertTrue(log.success)
