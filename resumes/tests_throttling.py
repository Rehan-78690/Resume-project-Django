"""
Tests for AI throttling configuration.
"""
from django.test import TestCase
from resumes.views import SectionRewriteAPIView
from rest_framework.throttling import ScopedRateThrottle


class AIThrottlingTests(TestCase):
    """Test AI endpoints have proper throttling configured."""
    
    def test_ai_rewrite_has_throttle_class(self):
        """SectionRewriteAPIView has throttle_classes set."""
        view = SectionRewriteAPIView()
        self.assertIn(ScopedRateThrottle, view.throttle_classes)
    
    def test_ai_rewrite_throttle_scope_correct(self):
        """SectionRewriteAPIView uses correct throttle scope."""
        view = SectionRewriteAPIView()
        self.assertEqual(view.throttle_scope, 'ai_rewrite')
