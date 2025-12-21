"""
Public serializers for safe data exposure via share links.
All nested serializers defined here to prevent internal field leakage.
"""
from rest_framework import serializers
from .models import (
    Resume, PersonalInfo, WorkExperience, Education,
    SkillCategory, SkillItem, Strength, Hobby,
    CustomSection, CustomItem, Template
)


# Template serializer (safe for public)
class TemplatePublicSerializer(serializers.ModelSerializer):
    """Public template info - no internal metadata."""
    class Meta:
        model = Template
        fields = ['id', 'name', 'slug', 'description', 'category', 'preview_image_url']
        read_only_fields = fields


# Nested entity serializers (no resume/user/category/section references)
class PersonalInfoPublicSerializer(serializers.ModelSerializer):
    """Public personal info - safe fields only."""
    class Meta:
        model = PersonalInfo
        fields = [
            'first_name', 'last_name', 'headline', 'summary',
            'email', 'phone', 'city', 'country',
            'website', 'linkedin_url', 'github_url', 'portfolio_url',
            'photo_url'
        ]
        read_only_fields = fields


class WorkExperiencePublicSerializer(serializers.ModelSerializer):
    """Public work experience - no resume reference."""
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'position_title', 'company_name', 'city', 'country',
            'start_date', 'end_date', 'is_current', 'description',
            'bullets', 'order'
        ]
        read_only_fields = fields


class EducationPublicSerializer(serializers.ModelSerializer):
    """Public education - no resume reference."""
    class Meta:
        model = Education
        fields = [
            'id', 'degree', 'field_of_study', 'school_name',
            'city', 'country', 'start_date', 'end_date',
            'is_current', 'description', 'order'
        ]
        read_only_fields = fields


class SkillItemPublicSerializer(serializers.ModelSerializer):
    """Public skill item - no category reference."""
    class Meta:
        model = SkillItem
        fields = ['id', 'name', 'level', 'order']
        read_only_fields = fields


class SkillCategoryPublicSerializer(serializers.ModelSerializer):
    """Public skill category - no resume reference."""
    items = SkillItemPublicSerializer(many=True, read_only=True)
    
    class Meta:
        model = SkillCategory
        fields = ['id', 'name', 'order', 'items']
        read_only_fields = fields


class StrengthPublicSerializer(serializers.ModelSerializer):
    """Public strength - no resume reference."""
    class Meta:
        model = Strength
        fields = ['id', 'label', 'order']
        read_only_fields = fields


class HobbyPublicSerializer(serializers.ModelSerializer):
    """Public hobby - no resume reference."""
    class Meta:
        model = Hobby
        fields = ['id', 'label', 'order']
        read_only_fields = fields


class CustomItemPublicSerializer(serializers.ModelSerializer):
    """Public custom item - no section reference."""
    class Meta:
        model = CustomItem
        fields = [
            'id', 'title', 'subtitle', 'meta', 'description',
            'start_date', 'end_date', 'is_current', 'order'
        ]
        read_only_fields = fields


class CustomSectionPublicSerializer(serializers.ModelSerializer):
    """Public custom section - no resume reference."""
    items = CustomItemPublicSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomSection
        fields = ['id', 'type', 'title', 'order', 'items']
        read_only_fields = fields


# Main public resume serializer
class ResumePublicSerializer(serializers.ModelSerializer):
    """
    Safe resume serializer for public sharing.
    Includes section_settings for frontend rendering.
    Excludes: user, ai_prompt, ai_model, status, is_ai_generated, deleted_at
    """
    template = TemplatePublicSerializer(read_only=True)
    personal_info = PersonalInfoPublicSerializer(read_only=True)
    work_experiences = WorkExperiencePublicSerializer(many=True, read_only=True)
    educations = EducationPublicSerializer(many=True, read_only=True)
    skill_categories = SkillCategoryPublicSerializer(many=True, read_only=True)
    strengths = StrengthPublicSerializer(many=True, read_only=True)
    hobbies = HobbyPublicSerializer(many=True, read_only=True)
    custom_sections = CustomSectionPublicSerializer(many=True, read_only=True)
    
    class Meta:
        model = Resume
        fields = [
            'id', 'title', 'template', 'language', 'target_role',
            'created_at', 'updated_at',
            'section_settings',
            'personal_info', 'work_experiences', 'educations',
            'skill_categories', 'strengths', 'hobbies', 'custom_sections'
        ]
        read_only_fields = fields
