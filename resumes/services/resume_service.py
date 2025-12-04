from django.db import transaction
from typing import Dict, Any, Optional
from ..models import (
    Resume, PersonalInfo, WorkExperience, Education,
    SkillCategory, SkillItem, Strength, Hobby,
    CustomSection, CustomItem
)


class ResumeService:
    """Service for resume operations with transaction safety"""
    
    @staticmethod
    def create_resume_from_draft(user, template_id: str, title: str, 
                                draft_payload: Dict[str, Any]) -> Resume:
        """Create a resume from AI draft with transaction safety"""
        
        with transaction.atomic():
            # Create resume
            resume = Resume.objects.create(
                user=user,
                title=title,
                template_id=template_id,
                language=draft_payload.get('personal_info', {}).get('language', 'en'),
                target_role=draft_payload.get('personal_info', {}).get('headline', ''),
                is_ai_generated=True,
                ai_model="gpt-4.1",
                ai_prompt=draft_payload.get('meta', {}).get('prompt', ''),
                status='draft'
            )
            
            # Create personal info
            pi_data = draft_payload.get('personal_info', {})
            if pi_data:
                PersonalInfo.objects.create(resume=resume, **pi_data)
            
            # Create work experiences
            for idx, exp_data in enumerate(draft_payload.get('work_experience', [])):
                exp_data['order'] = exp_data.get('order', idx)
                WorkExperience.objects.create(resume=resume, **exp_data)
            
            # Create education
            for idx, edu_data in enumerate(draft_payload.get('education', [])):
                edu_data['order'] = edu_data.get('order', idx)
                Education.objects.create(resume=resume, **edu_data)
            
            # Create skill categories with items
            for cat_idx, cat_data in enumerate(draft_payload.get('skill_categories', [])):
                items = cat_data.pop('items', [])
                cat_data['order'] = cat_data.get('order', cat_idx)
                category = SkillCategory.objects.create(resume=resume, **cat_data)
                
                for item_idx, item_data in enumerate(items):
                    item_data['order'] = item_data.get('order', item_idx)
                    SkillItem.objects.create(category=category, **item_data)
            
            # Create strengths
            for idx, strength in enumerate(draft_payload.get('strengths', [])):
                Strength.objects.create(
                    resume=resume,
                    label=strength,
                    order=idx
                )
            
            # Create hobbies
            for idx, hobby in enumerate(draft_payload.get('hobbies', [])):
                Hobby.objects.create(
                    resume=resume,
                    label=hobby,
                    order=idx
                )
            
            # Create custom sections with items
            for sec_idx, sec_data in enumerate(draft_payload.get('custom_sections', [])):
                items = sec_data.pop('items', [])
                sec_data['order'] = sec_data.get('order', sec_idx)
                section = CustomSection.objects.create(resume=resume, **sec_data)
                
                for item_idx, item_data in enumerate(items):
                    item_data['order'] = item_data.get('order', item_idx)
                    CustomItem.objects.create(section=section, **item_data)
            
            return resume
    
    @staticmethod
    def duplicate_resume(original_resume, new_title: Optional[str] = None):
        """Duplicate a resume with all related data"""
        
        if not new_title:
            new_title = f"{original_resume.title} (Copy)"
        
        with transaction.atomic():
            # Duplicate resume
            new_resume = Resume.objects.create(
                user=original_resume.user,
                title=new_title,
                template_id=original_resume.template_id,
                language=original_resume.language,
                target_role=original_resume.target_role,
                is_ai_generated=original_resume.is_ai_generated,
                ai_model=original_resume.ai_model,
                ai_prompt=original_resume.ai_prompt,
                status='draft'
            )
            
            # Duplicate personal info
            if hasattr(original_resume, 'personal_info'):
                pi = original_resume.personal_info
                PersonalInfo.objects.create(
                    resume=new_resume,
                    first_name=pi.first_name,
                    last_name=pi.last_name,
                    headline=pi.headline,
                    summary=pi.summary,
                    email=pi.email,
                    phone=pi.phone,
                    city=pi.city,
                    country=pi.country,
                    website=pi.website,
                    linkedin_url=pi.linkedin_url,
                    github_url=pi.github_url,
                    portfolio_url=pi.portfolio_url,
                    photo_url=pi.photo_url
                )
            
            # Duplicate work experiences
            for exp in original_resume.work_experiences.all():
                WorkExperience.objects.create(
                    resume=new_resume,
                    position_title=exp.position_title,
                    company_name=exp.company_name,
                    city=exp.city,
                    country=exp.country,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    description=exp.description,
                    bullets=exp.bullets.copy() if exp.bullets else [],
                    order=exp.order
                )
            
            # Duplicate education
            for edu in original_resume.educations.all():
                Education.objects.create(
                    resume=new_resume,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    school_name=edu.school_name,
                    city=edu.city,
                    country=edu.country,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    is_current=edu.is_current,
                    description=edu.description,
                    order=edu.order
                )
            
            # Duplicate skill categories with items
            for cat in original_resume.skill_categories.all():
                new_cat = SkillCategory.objects.create(
                    resume=new_resume,
                    name=cat.name,
                    order=cat.order
                )
                for skill in cat.items.all():
                    SkillItem.objects.create(
                        category=new_cat,
                        name=skill.name,
                        level=skill.level,
                        order=skill.order
                    )
            
            # Duplicate strengths
            for strength in original_resume.strengths.all():
                Strength.objects.create(
                    resume=new_resume,
                    label=strength.label,
                    order=strength.order
                )
            
            # Duplicate hobbies
            for hobby in original_resume.hobbies.all():
                Hobby.objects.create(
                    resume=new_resume,
                    label=hobby.label,
                    order=hobby.order
                )
            
            # Duplicate custom sections with items
            for section in original_resume.custom_sections.all():
                new_section = CustomSection.objects.create(
                    resume=new_resume,
                    type=section.type,
                    title=section.title,
                    order=section.order
                )
                for item in section.items.all():
                    CustomItem.objects.create(
                        section=new_section,
                        title=item.title,
                        subtitle=item.subtitle,
                        meta=item.meta,
                        description=item.description,
                        start_date=item.start_date,
                        end_date=item.end_date,
                        is_current=item.is_current,
                        order=item.order
                    )
            
            return new_resume