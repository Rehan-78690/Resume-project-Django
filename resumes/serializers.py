from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Resume, PersonalInfo, WorkExperience, Education,
    SkillCategory, SkillItem, Strength, Hobby,
    CustomSection, CustomItem, ResumeWizardSession, Template
)

User = get_user_model()


# === Custom Fields ===
class LenientURLField(serializers.URLField):
    """
    URLField that allows missing scheme (adds https://) and handles blank/None safely.
    """
    def to_internal_value(self, data):
        allow_blank = getattr(self, "allow_blank", False)
        allow_null = getattr(self, "allow_null", False)

        # None handling
        if data is None:
            if allow_null:
                return None
            if allow_blank:
                return ""
            self.fail("null")

        # String handling
        if isinstance(data, str):
            data = data.strip()

            if data == "":
                if allow_blank:
                    return ""
                self.fail("blank")

            lower_data = data.lower()
            if not (lower_data.startswith("http://") or lower_data.startswith("https://")):
                data = f"https://{data}"

        return super().to_internal_value(data)



# === Nested Serializers ===
class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'is_premium', 'preview_image_url', 'is_active', 'definition'
        ]
    
    def validate_definition(self, value):
        """Validate template definition schema"""
        # 1. Require dictionary
        if not isinstance(value, dict):
            raise serializers.ValidationError("Definition must be a dictionary")
        
        # 2. Require schema_version
        if "schema_version" not in value:
            raise serializers.ValidationError("Missing schema_version")
        if not isinstance(value["schema_version"], int):
            raise serializers.ValidationError("schema_version must be an integer")

        required_keys = ['layout', 'style', 'sections']
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Missing required key: {key}")
        
        # 3. Validate layout
        if not isinstance(value.get('layout'), dict):
             raise serializers.ValidationError("layout must be a dictionary")
        if 'type' not in value['layout']:
             raise serializers.ValidationError("Layout must have a 'type'")
             
        # 4. Validate sections
        sections = value.get('sections')
        if not isinstance(sections, dict):
            raise serializers.ValidationError("sections must be a dictionary")
            
        valid_areas = ['header', 'left', 'right', 'full']
        
        # Helper: Allow specific nested configs per section
        # We only strictly validate structure, but allow optional visual toggles like 'show_photo'
        
        for name, config in sections.items():
            if not isinstance(config, dict):
                raise serializers.ValidationError(f"Section {name} config must be a dict")
            
            # Check types for known keys
            if 'visible' in config and not isinstance(config['visible'], bool):
                raise serializers.ValidationError(f"Section {name} 'visible' must be bool")
            if 'order' in config:
                if not isinstance(config['order'], int) or config['order'] < 0:
                    raise serializers.ValidationError(f"Section {name} 'order' must be non-negative int")
            if 'area' in config and config['area'] not in valid_areas:
                 raise serializers.ValidationError(f"Section {name} 'area' invalid. Must be one of {valid_areas}")
            
            # Allow show_photo if it's a boolean (specifically for personal_info usually, but flexible)
            if 'show_photo' in config:
                if not isinstance(config['show_photo'], bool):
                    raise serializers.ValidationError(f"Section {name} 'show_photo' must be bool")

        return value
class PersonalInfoSerializer(serializers.ModelSerializer):
    # Use LenientURLField for all link fields
    website = LenientURLField(required=False, allow_blank=True)
    linkedin_url = LenientURLField(required=False, allow_blank=True)
    github_url = LenientURLField(required=False, allow_blank=True)
    portfolio_url = LenientURLField(required=False, allow_blank=True)
    photo_url = LenientURLField(required=False, allow_blank=True)
    
    class Meta:
        model = PersonalInfo
        fields = [
            'first_name', 'last_name', 'headline', 'summary',
            'email', 'phone', 'city', 'country',
            'website', 'linkedin_url', 'github_url', 'portfolio_url',
            'photo_url'
        ]


class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'position_title', 'company_name', 'city', 'country',
            'start_date', 'end_date', 'is_current', 'description',
            'bullets', 'order'
        ]


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            'id', 'degree', 'field_of_study', 'school_name',
            'city', 'country', 'start_date', 'end_date',
            'is_current', 'description', 'order'
        ]


class SkillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillItem
        fields = ['id', 'name', 'level', 'order']


class SkillCategorySerializer(serializers.ModelSerializer):
    items = SkillItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = SkillCategory
        fields = ['id', 'name', 'order', 'items']


class StrengthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Strength
        fields = ['id', 'label', 'order']


class HobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = Hobby
        fields = ['id', 'label', 'order']


class CustomItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomItem
        fields = [
            'id', 'title', 'subtitle', 'meta', 'description',
            'start_date', 'end_date', 'is_current', 'order'
        ]


class CustomSectionSerializer(serializers.ModelSerializer):
    items = CustomItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomSection
        fields = ['id', 'type', 'title', 'order', 'items']


# === Resume Serializers ===
class ResumeListSerializer(serializers.ModelSerializer):
    """Serializer for listing resumes (compact)"""
    class Meta:
        model = Resume
        fields = [
            'id', 'title', 'slug', 'template', 'language',
            'target_role', 'is_ai_generated', 'status',
            'created_at', 'updated_at'
        ]


class ResumeDetailSerializer(serializers.ModelSerializer):
    """Full resume with all nested data (for editor)"""
    template = TemplateSerializer(read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=Template.objects.filter(is_active=True),
        source='template',
        write_only=True
    )
    personal_info = PersonalInfoSerializer(read_only=True)
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    skill_categories = SkillCategorySerializer(many=True, read_only=True)
    strengths = StrengthSerializer(many=True, read_only=True)
    hobbies = HobbySerializer(many=True, read_only=True)
    custom_sections = CustomSectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Resume
        fields = [
            'id', 'user', 'title', 'slug', 'template', 'template_id', 'language',
            'target_role', 'is_ai_generated', 'ai_model', 'ai_prompt',
            'status', 'created_at', 'updated_at', 'last_edited_at',
            'section_settings',
            'personal_info', 'work_experiences', 'educations',
            'skill_categories', 'strengths', 'hobbies', 'custom_sections'
        ]
        read_only_fields = ['id', 'user', 'slug', 'created_at', 'updated_at']


class ResumeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new resume"""
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=Template.objects.filter(is_active=True),
        source='template'
    )
    
    class Meta:
        model = Resume
        fields = ['id', 'title', 'template_id', 'language', 'target_role']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ResumeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating resume metadata"""
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=Template.objects.filter(is_active=True),
        source='template',
        required=False
    )
    
    class Meta:
        model = Resume
        fields = ['title', 'template_id', 'template', 'language', 'target_role', 'status', 'section_settings']

    def validate_section_settings(self, value):
        """Validate user overrides for sections"""
        if not value:
            return value
            
        valid_sections = [
            'personal_info', 'work_experiences', 'educations',
            'skill_categories', 'strengths', 'hobbies', 'custom_sections'
        ]
        
        for key in value.keys():
            if key not in valid_sections:
                raise serializers.ValidationError(f"Invalid section key: {key}")
                
            setting = value[key]
            if not isinstance(setting, dict):
                 raise serializers.ValidationError(f"Setting for {key} must be a dict")
                 
            # Allow only specific overrides
            allowed_overrides = ['order', 'visible']
            for setting_key in setting.keys():
                if setting_key not in allowed_overrides:
                    raise serializers.ValidationError(f"Invalid override: {setting_key} in {key}")
            
            # Type validation
            if 'visible' in setting and not isinstance(setting['visible'], bool):
                raise serializers.ValidationError(f"invalid type for '{key}.visible': must be bool")
            
            if 'order' in setting:
                if not isinstance(setting['order'], int) or setting['order'] < 0:
                     raise serializers.ValidationError(f"invalid type for '{key}.order': must be non-negative int")
                    
        return value


# === AI Wizard Serializers ===
class QuickResumeInputSerializer(serializers.Serializer):
    """Input for AI quick resume generation"""
    name = serializers.CharField(max_length=200, required=False)
    target_role = serializers.CharField(max_length=200, required=True)
    job_description = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(min_value=0, max_value=50, required=False)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    location = serializers.CharField(max_length=200, required=False)
    language = serializers.CharField(max_length=10, default='en')
    seniority = serializers.ChoiceField(
        choices=['junior', 'mid', 'senior', 'lead', 'executive'],
        required=False
    )
    use_social_photo = serializers.BooleanField(default=False)
    photo_source = serializers.ChoiceField(
        choices=['google', 'facebook', None],
        required=False,
        allow_null=True
    )
    
    def validate(self, data):
        """Additional validation"""
        if data.get('use_social_photo') and not data.get('photo_source'):
            raise serializers.ValidationError(
                "photo_source must be provided when use_social_photo is True"
            )
        return data


class QuickResumeConfirmSerializer(serializers.Serializer):
    """Input for confirming AI draft"""
    wizard_id = serializers.UUIDField(required=True)
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=Template.objects.filter(is_active=True),
        required=True
    )
    title = serializers.CharField(max_length=200, required=True)


# === Section Rewrite Serializer ===
class SectionRewriteSerializer(serializers.Serializer):
    """Input for section-specific AI rewriting"""
    resume_id = serializers.UUIDField(required=True)
    section_type = serializers.ChoiceField(
        choices=['work_experience', 'summary', 'skills', 'strengths'],
        required=True
    )
    item_id = serializers.UUIDField(required=False)
    prompt = serializers.CharField(required=True)
    tone = serializers.ChoiceField(
        choices=['professional', 'concise', 'creative', 'formal'],
        default='professional'
    )


# === Helper for Wizard Sessions ===
class ResumeWizardSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeWizardSession
        fields = ['id', 'input_payload', 'draft_payload', 'created_at', 'expires_at', 'consumed']
        read_only_fields = ['created_at', 'expires_at', 'consumed']
    
    @classmethod
    def create_session(cls, user, input_payload, draft_payload, ttl_hours=2):
        """Helper to create a wizard session"""
        return ResumeWizardSession.objects.create(
            user=user,
            input_payload=input_payload,
            draft_payload=draft_payload,
            expires_at=timezone.now() + timedelta(hours=ttl_hours)
        )

# === New AI Serializers ===

class AISummarySerializer(serializers.Serializer):
    current_role = serializers.CharField(max_length=200)
    target_role = serializers.CharField(max_length=200)
    experience_years = serializers.IntegerField(min_value=0)
    keywords = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    tone = serializers.CharField(default='professional')

class AIBulletsSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=200)
    company = serializers.CharField(max_length=200)
    description = serializers.CharField(required=True)
    keywords = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    tone = serializers.CharField(default='professional')
    count = serializers.IntegerField(default=4, min_value=1, max_value=10)

class AIExperienceSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=200)
    company = serializers.CharField(max_length=200)
    keywords = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    tone = serializers.CharField(default='professional')

class AICoverLetterBaseSerializer(serializers.Serializer):
    resume_summary = serializers.CharField(required=True)
    job_description = serializers.CharField(required=True)
    tone = serializers.CharField(default='professional')

class AICoverLetterFullSerializer(serializers.Serializer):
    resume_id = serializers.UUIDField(required=True)
    company_name = serializers.CharField(max_length=200)
    job_title = serializers.CharField(max_length=200)
    job_description = serializers.CharField(required=False, allow_blank=True)
    tone = serializers.CharField(default='professional')
    language = serializers.CharField(default='en')
    key_points = serializers.ListField(child=serializers.CharField(), required=False, default=list)