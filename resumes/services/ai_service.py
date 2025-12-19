import json
import logging
import time
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from openai import OpenAI, RateLimitError, APIError, APITimeoutError
import openai
from ai_core.services import AILogService
from ai_core.models import AIUsageLog

logger = logging.getLogger(__name__)


class AIResumeService:
    """Production-grade AI service with retries and error handling"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
        self.max_retries = getattr(settings, 'OPENAI_MAX_RETRIES', 3)
        self.timeout = getattr(settings, 'OPENAI_TIMEOUT', 30)
    
    def generate_resume_from_input(
        self, 
        user,
        user_input: Dict[str, Any], 
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a structured resume from user input with retry logic"""
        
        prompt = self._build_prompt(user_input, user_data)
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=self.timeout
                )
                
                resume_data = json.loads(response.choices[0].message.content)
                validated_data = self._validate_and_normalize_resume(resume_data, user_input, user_data)
                
                # Log successful generation
                AILogService.log_usage(
                    user=user,
                    feature_type=AIUsageLog.FeatureType.RESUME_PREVIEW,
                    model_name=self.model,
                    prompt=prompt,
                    tokens_in=response.usage.prompt_tokens,
                    tokens_out=response.usage.completion_tokens,
                    success=True
                )
                logger.info(f"AI resume generated successfully for user {user.email}")
                return validated_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise ValueError("Failed to generate valid resume data")
                time.sleep(1)
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except (APIError, APITimeoutError) as e:
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Unexpected error in AI service (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1)
        
        # Log failure
        AILogService.log_usage(
            user=user,
            feature_type=AIUsageLog.FeatureType.RESUME_PREVIEW,
            model_name=self.model,
            prompt=prompt,
            tokens_in=0, 
            tokens_out=0,
            success=False,
            error_message="Failed after max retries"
        )
        raise Exception("Failed to generate resume after maximum retries")
    
    def generate_summary(self, user, current_role, target_role, experience_years, keywords=None, tone='professional'):
        prompt = f"""Write a professional resume summary for a {current_role} targeting a {target_role} position.
        Experience: {experience_years} years.
        Keywords to include: {', '.join(keywords) if keywords else 'None'}
        Tone: {tone}
        Length: 3-5 sentences. Focus on achievements and unique value proposition."""
        
        return self._generate_text(user, prompt, AIUsageLog.FeatureType.SUMMARY, tone)

    def generate_bullets(self, user, role, company, description, keywords=None, tone='professional', count=4):
        prompt = f"""Write {count} strong, achievement-oriented resume bullet points for:
        Role: {role}
        Company: {company}
        Context: {description}
        Keywords: {', '.join(keywords) if keywords else 'None'}
        Tone: {tone}
        
        Format: Return ONLY a JSON array of strings e.g. ["bullet 1", "bullet 2"]"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert resume writer."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            bullets = json.loads(content).get('bullets', [])
            if not bullets and isinstance(json.loads(content), list):
                 bullets = json.loads(content)
            
            # Fallback if specific key is expected but simple list returned
            if isinstance(json.loads(content), dict) and not bullets:
                 # Check values
                 bullets = list(json.loads(content).values())[0]

            AILogService.log_usage(
                user=user,
                feature_type=AIUsageLog.FeatureType.BULLETS,
                model_name=self.model,
                prompt=prompt,
                tokens_in=response.usage.prompt_tokens,
                tokens_out=response.usage.completion_tokens,
                success=True
            )
            return bullets
        except Exception as e:
            AILogService.log_usage(user, AIUsageLog.FeatureType.BULLETS, self.model, prompt, success=False, error_message=str(e))
            raise e

    def generate_experience(self, user, role, company, keywords=None, tone='professional'):
        prompt = f"""Write a compelling job description paragraph for:
        Role: {role}
        Company: {company}
        Keywords: {', '.join(keywords) if keywords else 'None'}
        Tone: {tone}
        Length: 2-3 sentences."""
        
        return self._generate_text(user, prompt, AIUsageLog.FeatureType.EXPERIENCE, tone)

    def generate_cover_letter_base(self, user, resume_summary, job_description, tone='professional'):
        prompt = f"""Write the body paragraphs of a cover letter based on:
        My Background: {resume_summary}
        Job Description: {job_description}
        Tone: {tone}
        
        Requirements:
        1. 3-4 paragraphs
        2. Focus on matching my skills to job requirements
        3. Professional and engaging
        4. Return ONLY the body text."""
        
        return self._generate_text(user, prompt, AIUsageLog.FeatureType.COVER_LETTER_BASE, tone)

    def generate_cover_letter_full(self, user, resume_data, job_details, tone='professional'):
        prompt = f"""Write a full cover letter.
        Candidate: {resume_data.get('name')}
        Target Company: {job_details.get('company')}
        Target Role: {job_details.get('title')}
        Job Description: {job_details.get('description')}
        Candidate Summary: {resume_data.get('summary')}
        Key Skills: {', '.join(resume_data.get('skills', []))}
        Tone: {tone}
        
        Return JSON: {{ "body": "...", "subject": "..." }}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert cover letter writer."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            data = json.loads(response.choices[0].message.content)
            
            AILogService.log_usage(
                user=user,
                feature_type=AIUsageLog.FeatureType.COVER_LETTER_FULL,
                model_name=self.model,
                prompt=prompt,
                tokens_in=response.usage.prompt_tokens,
                tokens_out=response.usage.completion_tokens,
                success=True
            )
            return data
        except Exception as e:
            AILogService.log_usage(user, AIUsageLog.FeatureType.COVER_LETTER_FULL, self.model, prompt, success=False, error_message=str(e))
            raise e

    def _generate_text(self, user, prompt, feature_type, tone):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a professional career coach. Tone: {tone}"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            text = response.choices[0].message.content.strip()
            
            AILogService.log_usage(
                user=user,
                feature_type=feature_type,
                model_name=self.model,
                prompt=prompt,
                tokens_in=response.usage.prompt_tokens,
                tokens_out=response.usage.completion_tokens,
                success=True
            )
            return text
        except Exception as e:
            AILogService.log_usage(user, feature_type, self.model, prompt, success=False, error_message=str(e))
            raise e
    
    def rewrite_section(self, user, original_text: str, prompt: str, tone: str = 'professional') -> str:
        """Rewrite a section with AI with retry logic"""
        
        system_prompt = f"""You are a professional resume editor. Rewrite the following content based on the user's request.
        Tone: {tone}
        
        Instructions:
        1. Keep the same meaning and key information
        2. Improve clarity and impact
        3. Use professional language
        4. Maintain similar length
        5. Focus on achievements and results
        6. Return only the rewritten text, no explanations"""
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Original text: {original_text}\n\nUser request: {prompt}"}
                    ],
                    temperature=0.5,
                    max_tokens=500,
                    timeout=self.timeout
                )
                
                rewritten = response.choices[0].message.content.strip()
                
                AILogService.log_usage(
                    user=user,
                    feature_type=AIUsageLog.FeatureType.REWRITE,
                    model_name=self.model,
                    prompt=f"Original: {original_text}\nPrompt: {prompt}",
                    tokens_in=response.usage.prompt_tokens,
                    tokens_out=response.usage.completion_tokens,
                    success=True
                )
                
                logger.info(f"Section rewritten successfully (tone: {tone})")
                return rewritten
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit in rewrite (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    AILogService.log_usage(user, AIUsageLog.FeatureType.REWRITE, self.model, prompt, success=False, error_message=str(e))
                    return original_text
                time.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Error in rewrite (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    AILogService.log_usage(user, AIUsageLog.FeatureType.REWRITE, self.model, prompt, success=False, error_message=str(e))
                    return original_text
                time.sleep(1)
        
        return original_text  # Fallback to original text
    
    def _build_prompt(self, user_input: Dict[str, Any], user_data: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for the AI"""
        
        name = user_input.get('name', '')
        if not name:
            name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        
        prompt_parts = [
            "You are an expert resume writer. Generate a professional resume with the following details:",
            "",
            f"Name: {name}",
            f"Target Role: {user_input.get('target_role', 'Professional')}",
        ]
        
        if user_input.get('job_description'):
            prompt_parts.append(f"Job Description Context: {user_input['job_description']}")
        
        if user_input.get('experience_years'):
            seniority = self._get_seniority_level(user_input['experience_years'])
            prompt_parts.append(f"Experience Level: {seniority} ({user_input['experience_years']} years)")
        
        if user_input.get('seniority'):
            prompt_parts.append(f"Desired Seniority: {user_input['seniority']}")
        
        if user_input.get('skills'):
            prompt_parts.append(f"Key Skills: {', '.join(user_input['skills'])}")
        
        if user_input.get('location'):
            prompt_parts.append(f"Location: {user_input['location']}")
        
        prompt_parts.extend([
            "",
            "Requirements:",
            "1. Generate realistic but fictional content that matches the target role and experience",
            "2. Create a compelling professional summary (3-5 sentences)",
            "3. Include 2-4 work experiences with 3-5 bullet points each",
            "4. Include 1-2 education entries",
            "5. Organize skills into logical categories with appropriate skill levels",
            "6. Include 4-6 professional strengths",
            "7. Include 2-4 relevant hobbies/interests",
            "8. Include 1-2 custom sections (e.g., Projects, Certifications)",
            "9. All dates should be in YYYY-MM or YYYY format",
            "10. Be specific and quantitative where possible (metrics, percentages)",
            "",
            "Output must be in this exact JSON format:"
        ])
        
        prompt_parts.append(self._get_json_schema())
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        return """You are a professional resume writer and career coach with 10+ years of experience.
        You create realistic, compelling resumes that help candidates stand out.
        You are accurate, professional, and focus on achievements and results."""
    
    def _get_json_schema(self) -> str:
        return json.dumps({
            "personal_info": {
                "first_name": "string",
                "last_name": "string",
                "headline": "string (e.g., 'Senior Software Engineer')",
                "email": "string (realistic email)",
                "phone": "string (optional)",
                "city": "string",
                "country": "string",
                "summary": "string (professional summary, 3-5 sentences)",
                "website": "string (optional)",
                "linkedin_url": "string (optional)",
                "github_url": "string (optional)",
                "photo_url": "string (leave empty)"
            },
            "work_experience": [
                {
                    "position_title": "string",
                    "company_name": "string",
                    "city": "string",
                    "country": "string",
                    "start_date": "string (YYYY-MM)",
                    "end_date": "string (YYYY-MM or empty for current)",
                    "is_current": "boolean",
                    "description": "string (optional)",
                    "bullets": ["string", "string", "string"]
                }
            ],
            "education": [
                {
                    "degree": "string",
                    "field_of_study": "string",
                    "school_name": "string",
                    "city": "string",
                    "country": "string",
                    "start_date": "string (YYYY or YYYY-MM)",
                    "end_date": "string (YYYY or YYYY-MM)",
                    "is_current": "boolean",
                    "description": "string (optional)"
                }
            ],
            "skill_categories": [
                {
                    "name": "string",
                    "items": [
                        {
                            "name": "string",
                            "level": "string (beginner|intermediate|professional|expert)"
                        }
                    ]
                }
            ],
            "strengths": ["string", "string", "string"],
            "hobbies": ["string", "string"],
            "custom_sections": [
                {
                    "type": "string (achievements|projects|awards|certificates|languages|custom)",
                    "title": "string",
                    "items": [
                        {
                            "title": "string",
                            "subtitle": "string (optional)",
                            "meta": "string (optional)",
                            "description": "string",
                            "start_date": "string (optional)",
                            "end_date": "string (optional)",
                            "is_current": "boolean"
                        }
                    ]
                }
            ]
        }, indent=2)
    
    def _validate_and_normalize_resume(self, resume_data: Dict[str, Any], 
                                      user_input: Dict[str, Any],
                                      user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize the AI-generated resume"""
        
        # Ensure all required top-level keys exist
        defaults = {
            "personal_info": {},
            "work_experience": [],
            "education": [],
            "skill_categories": [],
            "strengths": [],
            "hobbies": [],
            "custom_sections": []
        }
        
        for key, default in defaults.items():
            if key not in resume_data:
                resume_data[key] = default
        
        # Merge with actual user data
        personal_info = resume_data["personal_info"]
        
        # Use actual user name if provided
        if user_input.get('name'):
            name_parts = user_input['name'].split(' ', 1)
            personal_info['first_name'] = name_parts[0]
            if len(name_parts) > 1:
                personal_info['last_name'] = name_parts[1]
        
        # Use actual user email
        if user_data.get('email'):
            personal_info['email'] = user_data['email']
        
        # Use social photo if requested and available
        if user_input.get('use_social_photo') and user_data.get('photo_url'):
            personal_info['photo_url'] = user_data['photo_url']
        
        # Normalize dates and ensure required fields
        for exp in resume_data.get("work_experience", []):
            if exp.get('end_date', '').lower() in ['present', 'current', '']:
                exp['is_current'] = True
                exp['end_date'] = ''
        
        # Ensure skill categories have items
        for category in resume_data.get("skill_categories", []):
            if 'items' not in category:
                category['items'] = []
        
        # Ensure custom sections have items
        for section in resume_data.get("custom_sections", []):
            if 'items' not in section:
                section['items'] = []
        
        return resume_data
    
    def _get_seniority_level(self, years: int) -> str:
        """Map years of experience to seniority level"""
        if years <= 2:
            return "Junior"
        elif years <= 5:
            return "Mid-level"
        elif years <= 10:
            return "Senior"
        else:
            return "Expert"