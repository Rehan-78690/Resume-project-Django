from rest_framework import serializers
from .models import CoverLetter, CoverLetterTemplate

class CoverLetterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverLetterTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'is_premium', 'preview_image_url', 'is_active', 'definition'
        ]


class CoverLetterSerializer(serializers.ModelSerializer):
    template_detail = CoverLetterTemplateSerializer(source='template', read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=CoverLetterTemplate.objects.filter(is_active=True),
        source='template',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = CoverLetter
        fields = [
            'id', 'user', 'linked_resume', 'template', 'template_id', 'template_detail',
            'title', 'company_name', 'job_title', 'job_description',
            'body', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class CoverLetterGenerateSerializer(serializers.Serializer):
    """Serializer for AI Generation of CL"""
    resume_id = serializers.UUIDField(required=True)
    company_name = serializers.CharField(max_length=200)
    job_title = serializers.CharField(max_length=200)
    job_description = serializers.CharField(required=False, allow_blank=True)
    tone = serializers.CharField(default='professional')
