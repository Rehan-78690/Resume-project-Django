from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Resume, PersonalInfo, WorkExperience, Education,
    SkillCategory, SkillItem, Strength, Hobby,
    CustomSection, CustomItem, ResumeWizardSession
)

User = get_user_model()


# === Nested Serializers ===
class PersonalInfoSerializer(serializers.ModelSerializer):
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
            'id', 'title', 'slug', 'template_id', 'language',
            'target_role', 'is_ai_generated', 'status',
            'created_at', 'updated_at'
        ]


class ResumeDetailSerializer(serializers.ModelSerializer):
    """Full resume with all nested data (for editor)"""
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
            'id', 'user', 'title', 'slug', 'template_id', 'language',
            'target_role', 'is_ai_generated', 'ai_model', 'ai_prompt',
            'status', 'created_at', 'updated_at', 'last_edited_at',
            'personal_info', 'work_experiences', 'educations',
            'skill_categories', 'strengths', 'hobbies', 'custom_sections'
        ]
        read_only_fields = ['id', 'user', 'slug', 'created_at', 'updated_at']


class ResumeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new resume"""
    class Meta:
        model = Resume
        fields = ['title', 'template_id', 'language', 'target_role']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ResumeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating resume metadata"""
    class Meta:
        model = Resume
        fields = ['title', 'template_id', 'language', 'target_role', 'status']


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
    template_id = serializers.CharField(max_length=20, required=True)
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