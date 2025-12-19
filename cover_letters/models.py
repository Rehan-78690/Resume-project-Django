import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class CoverLetter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cover_letters"
    )
    linked_resume = models.ForeignKey(
        "resumes.Resume",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cover_letters"
    )
    
    template = models.ForeignKey(
        "CoverLetterTemplate",
        on_delete=models.PROTECT,
        db_column="template_id",
        default="standard-1"
    )
    
    title = models.CharField(max_length=200, default="My Cover Letter")
    
    # Target Job Details
    company_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    job_description = models.TextField(blank=True) # For AI context
    
    # Content
    body = models.TextField(blank=True)
    
    status = models.CharField(
        max_length=20,
        default="draft",
        choices=[("draft", "Draft"), ("published", "Published")]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])


class CoverLetterTemplate(models.Model):
    """Template for cover letter styling and layout."""
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default="professional")
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    preview_image_url = models.CharField(max_length=500, blank=True)
    
    # Template definition (layout, styles, sections)
    definition = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

