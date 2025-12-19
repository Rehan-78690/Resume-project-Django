from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class AIUsageLog(models.Model):
    class FeatureType(models.TextChoices):
        SUMMARY = "summary", "Summary Generation"
        BULLETS = "bullets", "Bullet Point Optimization"
        EXPERIENCE = "experience", "Experience Description"
        REWRITE = "rewrite", "Text Rewrite"
        COVER_LETTER_BASE = "cover_letter_base", "Cover Letter Base"
        COVER_LETTER_FULL = "cover_letter_full", "Full Cover Letter"
        RESUME_PREVIEW = "resume_preview", "Resume Preview"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_logs"
    )
    feature_type = models.CharField(
        max_length=50,
        choices=FeatureType.choices,
        default=FeatureType.OTHER
    )
    prompt_hash = models.CharField(max_length=255, blank=True)
    model_name = models.CharField(max_length=50)
    
    # Metadata
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    
    # Result
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'feature_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.feature_type} - {self.created_at}"
