"""
Section-specific ViewSets for resume sections.
All endpoints are scoped to a resume and require authentication.
Ownership is enforced: users can only access their own resume sections (staff can access any).
"""
import logging
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import (
    Resume, PersonalInfo, WorkExperience, Education,
    SkillCategory, SkillItem, Strength, Hobby,
    CustomSection, CustomItem
)
from .serializers import (
    PersonalInfoSerializer, WorkExperienceSerializer,
    EducationSerializer, SkillCategorySerializer, SkillItemSerializer,
    StrengthSerializer, HobbySerializer,
    CustomSectionSerializer, CustomItemSerializer
)

logger = logging.getLogger(__name__)


class ResumeSectionMixin:
    """Mixin to provide secure resume scoping for section ViewSets."""
    
    def get_resume(self):
        """
        Get the resume, enforcing ownership unless staff/superuser.
        Returns 404 if not found or not owned by user.
        """
        resume_id = self.kwargs.get('resume_id')
        if not resume_id:
            return None
            
        # Staff can access any resume
        if self.request.user.is_staff or self.request.user.is_superuser:
            resume = get_object_or_404(
                Resume,
                id=resume_id,
                deleted_at__isnull=True
            )
        else:
            # Regular users only their own resumes
            resume = get_object_or_404(
                Resume,
                id=resume_id,
                user=self.request.user,
                deleted_at__isnull=True
            )
        return resume
    
    def get_queryset(self):
        """Override to filter by resume and ownership."""
        resume = self.get_resume()
        if not resume:
            return self.queryset.none()
        
        # Filter by resume
        qs = self.queryset.filter(resume=resume)
        
        # If not staff, double-check ownership via resume
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            qs = qs.filter(resume__user=self.request.user, resume__deleted_at__isnull=True)
        
        return qs
    
    def perform_create(self, serializer):
        """Set resume on creation."""
        resume = self.get_resume()
        serializer.save(resume=resume)


class PersonalInfoViewSet(ResumeSectionMixin, viewsets.GenericViewSet):
    """
    Singleton endpoint for PersonalInfo.
    GET/PATCH/PUT only (no POST/DELETE since it's one-to-one with Resume).
    """
    queryset = PersonalInfo.objects.all()
    serializer_class = PersonalInfoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create PersonalInfo for this resume."""
        resume = self.get_resume()
        obj, created = PersonalInfo.objects.get_or_create(resume=resume)
        return obj
    
    def retrieve(self, request, resume_id=None):
        """GET personal info."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, resume_id=None):
        """PUT personal info."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def partial_update(self, request, resume_id=None):
        """PATCH personal info."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WorkExperienceViewSet(ResumeSectionMixin, viewsets.ModelViewSet):
    """CRUD for WorkExperience scoped to a resume."""
    queryset = WorkExperience.objects.all()
    serializer_class = WorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]


class EducationViewSet(ResumeSectionMixin, viewsets.ModelViewSet):
    """CRUD for Education scoped to a resume."""
    queryset = Education.objects.all()
    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated]


class StrengthViewSet(ResumeSectionMixin, viewsets.ModelViewSet):
    """CRUD for Strength scoped to a resume."""
    queryset = Strength.objects.all()
    serializer_class = StrengthSerializer
    permission_classes = [permissions.IsAuthenticated]


class HobbyViewSet(ResumeSectionMixin, viewsets.ModelViewSet):
    """CRUD for Hobby scoped to a resume."""
    queryset = Hobby.objects.all()
    serializer_class = HobbySerializer
    permission_classes = [permissions.IsAuthenticated]


class SkillCategoryViewSet(ResumeSectionMixin, viewsets.ModelViewSet):
    """CRUD for SkillCategory scoped to a resume."""
    queryset = SkillCategory.objects.all()
    serializer_class = SkillCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class SkillItemViewSet(viewsets.ModelViewSet):
    """
    CRUD for SkillItem scoped to a SkillCategory (which is scoped to a resume).
    Enforces that category belongs to the resume and user owns it.
    """
    queryset = SkillItem.objects.all()
    serializer_class = SkillItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_category(self):
        """Get the skill category, enforcing ownership."""
        resume_id = self.kwargs.get('resume_id')
        category_id = self.kwargs.get('category_id')
        
        # Staff can access any
        if self.request.user.is_staff or self.request.user.is_superuser:
            category = get_object_or_404(
                SkillCategory,
                id=category_id,
                resume_id=resume_id,
                resume__deleted_at__isnull=True
            )
        else:
            # Ensure category belongs to resume, and resume belongs to user
            category = get_object_or_404(
                SkillCategory,
                id=category_id,
                resume_id=resume_id,
                resume__user=self.request.user,
                resume__deleted_at__isnull=True
            )
        return category
    
    def get_queryset(self):
        """Filter by category."""
        category = self.get_category()
        return self.queryset.filter(category=category)
    
    def perform_create(self, serializer):
        """Set category on creation."""
        category = self.get_category()
        serializer.save(category=category)


class CustomSectionViewSet(ResumeSectionMixin, viewsets.ModelViewSet):
    """CRUD for CustomSection scoped to a resume."""
    queryset = CustomSection.objects.all()
    serializer_class = CustomSectionSerializer
    permission_classes = [permissions.IsAuthenticated]


class CustomItemViewSet(viewsets.ModelViewSet):
    """
    CRUD for CustomItem scoped to a CustomSection (which is scoped to a resume).
    Enforces that section belongs to the resume and user owns it.
    """
    queryset = CustomItem.objects.all()
    serializer_class = CustomItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_section(self):
        """Get the custom section, enforcing ownership."""
        resume_id = self.kwargs.get('resume_id')
        section_id = self.kwargs.get('section_id')
        
        # Staff can access any
        if self.request.user.is_staff or self.request.user.is_superuser:
            section = get_object_or_404(
                CustomSection,
                id=section_id,
                resume_id=resume_id,
                resume__deleted_at__isnull=True
            )
        else:
            # Ensure section belongs to resume, and resume belongs to user
            section = get_object_or_404(
                CustomSection,
                id=section_id,
                resume_id=resume_id,
                resume__user=self.request.user,
                resume__deleted_at__isnull=True
            )
        return section
    
    def get_queryset(self):
        """Filter by section."""
        section = self.get_section()
        return self.queryset.filter(section=section)
    
    def perform_create(self, serializer):
        """Set section on creation."""
        section = self.get_section()
        serializer.save(section=section)
