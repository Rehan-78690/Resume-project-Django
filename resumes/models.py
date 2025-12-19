import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class Template(models.Model):
    id = models.CharField(primary_key=True, max_length=50)  # e.g. "classic-1"
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default="professional")  # professional, creative, etc
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    preview_image_url = models.CharField(max_length=500, blank=True)
    
    # Backend-driven template definition (layout, styles, sections)
    definition = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Resume(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"
    
    
    class Language(models.TextChoices):
        EN = "en", "English"
        DE = "de", "German"
        FR = "fr", "French"
        ES = "es", "Spanish"
    
    class AIModel(models.TextChoices):
        GPT_4 = "gpt-4", "GPT-4"
        GPT_4_1 = "gpt-4.1", "GPT-4.1"
        CLAUDE_3 = "claude-3", "Claude 3"
    

    
    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes"
    )
    title = models.CharField(max_length=200, default="My Resume")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    
    # Styling
    template = models.ForeignKey(
        "Template",
        on_delete=models.PROTECT,
        db_column="template_id",
        verbose_name="Template",
        default="classic-1"
    )
    
    # User overrides for section ordering/visibility (drag & drop)
    section_settings = models.JSONField(default=dict, blank=True)
    
    language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.EN
    )
    
    # Metadata
    target_role = models.CharField(max_length=200, blank=True)
    is_ai_generated = models.BooleanField(default=False)
    ai_model = models.CharField(
        max_length=20,
        choices=AIModel.choices,
        blank=True
    )
    ai_prompt = models.JSONField(default=dict, blank=True)  # Store input for audit
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_edited_at = models.DateTimeField(auto_now=True)
    
    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        # Generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Resume.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    def soft_delete(self):
        """Soft delete the resume"""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def restore(self):
        """Restore soft-deleted resume"""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])


class PersonalInfo(models.Model):
    resume = models.OneToOneField(
        Resume,
        on_delete=models.CASCADE,
        related_name="personal_info"
    )
    
    # Basic info
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    headline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    
    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Links
    website = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    
    # Photo
    photo_url = models.URLField(blank=True)
    
    class Meta:
        verbose_name_plural = "Personal info"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.resume.title}"


class WorkExperience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="work_experiences"
    )
    
    # Job details
    position_title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Dates as strings (YYYY-MM) for AI compatibility
    start_date = models.CharField(max_length=10)  # YYYY-MM or YYYY
    end_date = models.CharField(max_length=10, blank=True)  # YYYY-MM, YYYY, or empty
    is_current = models.BooleanField(default=False)
    
    # Content
    description = models.TextField(blank=True)
    bullets = models.JSONField(default=list)  # List of bullet points
    
    # Ordering
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-start_date', 'order']
    
    def __str__(self):
        return f"{self.position_title} at {self.company_name}"


class Education(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="educations"
    )
    
    # Education details
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)
    school_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Dates
    start_date = models.CharField(max_length=10, blank=True)  # YYYY or YYYY-MM
    end_date = models.CharField(max_length=10, blank=True)  # YYYY or YYYY-MM
    is_current = models.BooleanField(default=False)
    
    # Content
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-end_date', 'order']
    
    def __str__(self):
        return f"{self.degree} - {self.school_name}"


class SkillCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="skill_categories"
    )
    
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name_plural = "Skill categories"
    
    def __str__(self):
        return f"{self.name} - {self.resume.title}"


class SkillItem(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        PROFESSIONAL = "professional", "Professional"
        EXPERT = "expert", "Expert"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.CASCADE,
        related_name="items"
    )
    
    name = models.CharField(max_length=100)
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.INTERMEDIATE
    )
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.name} ({self.level})"


class Strength(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="strengths"
    )
    
    label = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.label


class Hobby(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="hobbies"
    )
    
    label = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name_plural = "Hobbies"
    
    def __str__(self):
        return self.label


class CustomSection(models.Model):
    class SectionType(models.TextChoices):
        ACHIEVEMENTS = "achievements", "Achievements"
        PROJECTS = "projects", "Projects"
        AWARDS = "awards", "Awards"
        CERTIFICATES = "certificates", "Certificates"
        LANGUAGES = "languages", "Languages"
        PUBLICATIONS = "publications", "Publications"
        CUSTOM = "custom", "Custom"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="custom_sections"
    )
    
    type = models.CharField(
        max_length=20,
        choices=SectionType.choices,
        default=SectionType.CUSTOM
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"


class CustomItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(
        CustomSection,
        on_delete=models.CASCADE,
        related_name="items"
    )
    
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    meta = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    
    # For items with dates (certificates, projects, etc.)
    start_date = models.CharField(max_length=10, blank=True)
    end_date = models.CharField(max_length=10, blank=True)
    is_current = models.BooleanField(default=False)
    
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title


class ResumeWizardSession(models.Model):
    """Temporary storage for AI-generated resume drafts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wizard_sessions"
    )
    
    input_payload = models.JSONField()  # User input
    draft_payload = models.JSONField()  # AI-generated draft
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'consumed']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def mark_consumed(self):
        self.consumed = True
        self.save(update_fields=['consumed'])
    
    def __str__(self):
        return f"Wizard {self.id} - {self.user.email}"


class ShareLink(models.Model):
    class ResourceType(models.TextChoices):
        RESUME = "resume", "Resume"
        COVER_LETTER = "cover_letter", "Cover Letter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="share_links"
    )
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    resource_id = models.UUIDField()  # Can point to Resume or CoverLetter
    
    token = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['resource_id', 'resource_type']),
        ]

    def __str__(self):
        return f"Share {self.resource_type}/{self.resource_id} ({self.token})"


class ResumeVersion(models.Model):
    """Stores snapshots of resume versions for history/restore."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    snapshot_data = models.JSONField()  # Full resume state
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_versions"
    )

    class Meta:
        unique_together = [['resume', 'version_number']]
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['resume', '-version_number']),
        ]

    def __str__(self):
        return f"{self.resume.title} v{self.version_number}"