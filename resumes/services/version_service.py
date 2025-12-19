from django.db import transaction
from django.shortcuts import get_object_or_404
from resumes.models import Resume, ResumeVersion
from resumes.serializers import ResumeDetailSerializer
import logging

logger = logging.getLogger(__name__)

MAX_VERSIONS_PER_RESUME = 25


class VersionService:
    """Service for managing resume version history."""
    
    @staticmethod
    def create_snapshot(resume, user):
        """
        Create a snapshot of the current resume state.
        
        Args:
            resume: Resume instance
            user: User creating the snapshot
            
        Returns:
            ResumeVersion instance
        """
        # Serialize current resume state
        serializer = ResumeDetailSerializer(resume)
        snapshot_data = serializer.data
        
        # Get next version number
        last_version = ResumeVersion.objects.filter(resume=resume).first()
        version_number = (last_version.version_number + 1) if last_version else 1
        
        # Create version
        version = ResumeVersion.objects.create(
            resume=resume,
            version_number=version_number,
            snapshot_data=snapshot_data,
            created_by=user
        )
        
        # Prune old versions if exceeding limit
        VersionService._prune_old_versions(resume)
        
        logger.info(f"Created version {version_number} for resume {resume.id}")
        return version
    
    @staticmethod
    def _prune_old_versions(resume):
        """Remove old versions exceeding MAX_VERSIONS_PER_RESUME."""
        versions = ResumeVersion.objects.filter(resume=resume).order_by('-version_number')
        if versions.count() > MAX_VERSIONS_PER_RESUME:
            to_delete = versions[MAX_VERSIONS_PER_RESUME:]
            deleted_count = len(to_delete)
            for version in to_delete:
                version.delete()
            logger.info(f"Pruned {deleted_count} old versions for resume {resume.id}")
    
    @staticmethod
    @transaction.atomic
    def restore_version(resume, version_id, user):
        """
        Restore resume to a previous version.
        
        Args:
            resume: Resume instance
            version_id: UUID of the version to restore
            user: User performing the restore
            
        Returns:
            Updated Resume instance
        """
        version = get_object_or_404(
            ResumeVersion,
            id=version_id,
            resume=resume
        )
        
        snapshot = version.snapshot_data
        
        # Update resume core fields
        resume.title = snapshot.get('title', resume.title)
        resume.target_role = snapshot.get('target_role', resume.target_role)
        resume.language = snapshot.get('language', resume.language)
        resume.status = snapshot.get('status', resume.status)
        resume.section_settings = snapshot.get('section_settings', {})
        resume.save()
        
        # Update personal info
        if 'personal_info' in snapshot and hasattr(resume, 'personal_info'):
            pi_data = snapshot['personal_info']
            pi = resume.personal_info
            for field, value in pi_data.items():
                if hasattr(pi, field):
                    setattr(pi, field, value)
            pi.save()
        
        # Clear and restore work experiences
        resume.work_experiences.all().delete()
        if 'work_experiences' in snapshot:
            from resumes.models import WorkExperience
            for idx, we_data in enumerate(snapshot['work_experiences']):
                we_data.pop('id', None)  # Remove ID to create new
                WorkExperience.objects.create(
                    resume=resume,
                    order=idx,
                    **{k: v for k, v in we_data.items() if k not in ['id']}
                )
        
        # Clear and restore educations
        resume.educations.all().delete()
        if 'educations' in snapshot:
            from resumes.models import Education
            for idx, ed_data in enumerate(snapshot['educations']):
                ed_data.pop('id', None)
                Education.objects.create(
                    resume=resume,
                    order=idx,
                    **{k: v for k, v in ed_data.items() if k not in ['id']}
                )
        
        # Clear and restore skill categories with items
        resume.skill_categories.all().delete()
        if 'skill_categories' in snapshot:
            from resumes.models import SkillCategory, SkillItem
            for sc_idx, sc_data in enumerate(snapshot['skill_categories']):
                items = sc_data.pop('items', [])
                sc_data.pop('id', None)
                category = SkillCategory.objects.create(
                    resume=resume,
                    order=sc_idx,
                    **{k: v for k, v in sc_data.items() if k not in ['id', 'items']}
                )
                for item_idx, item_data in enumerate(items):
                    item_data.pop('id', None)
                    SkillItem.objects.create(
                        category=category,
                        order=item_idx,
                        **{k: v for k, v in item_data.items() if k not in ['id']}
                    )
        
        # Clear and restore strengths
        resume.strengths.all().delete()
        if 'strengths' in snapshot:
            from resumes.models import Strength
            for idx, st_data in enumerate(snapshot['strengths']):
                st_data.pop('id', None)
                Strength.objects.create(
                    resume=resume,
                    order=idx,
                    **{k: v for k, v in st_data.items() if k not in ['id']}
                )
        
        # Clear and restore hobbies
        resume.hobbies.all().delete()
        if 'hobbies' in snapshot:
            from resumes.models import Hobby
            for idx, hb_data in enumerate(snapshot['hobbies']):
                hb_data.pop('id', None)
                Hobby.objects.create(
                    resume=resume,
                    order=idx,
                    **{k: v for k, v in hb_data.items() if k not in ['id']}
                )
        
        # Clear and restore custom sections with items
        resume.custom_sections.all().delete()
        if 'custom_sections' in snapshot:
            from resumes.models import CustomSection, CustomItem
            for cs_idx, cs_data in enumerate(snapshot['custom_sections']):
                items = cs_data.pop('items', [])
                cs_data.pop('id', None)
                section = CustomSection.objects.create(
                    resume=resume,
                    order=cs_idx,
                    **{k: v for k, v in cs_data.items() if k not in ['id', 'items']}
                )
                for item_idx, item_data in enumerate(items):
                    item_data.pop('id', None)
                    CustomItem.objects.create(
                        section=section,
                        order=item_idx,
                        **{k: v for k, v in item_data.items() if k not in ['id']}
                    )
        
        logger.info(f"Restored resume {resume.id} to version {version.version_number}")
        return resume
