"""
Public serializers for cover letter safe data exposure via share links.
"""
from rest_framework import serializers
from cover_letters.models import CoverLetter


class CoverLetterPublicSerializer(serializers.ModelSerializer):
    """
    Safe cover letter serializer for public sharing.
    Excludes: user, linked_resume, deleted_at, job_description (may contain sensitive info)
    """
    class Meta:
        model = CoverLetter
        fields = [
            'id', 'title', 'company_name', 'job_title',
            'body', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
