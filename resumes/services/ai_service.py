import json
import logging
import time
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from openai import OpenAI, RateLimitError, APIError, APITimeoutError
import openai

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
                logger.info(f"AI resume generated successfully for user {user_data.get('email')}")
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
        
        raise Exception("Failed to generate resume after maximum retries")
    
    def rewrite_section(self, original_text: str, prompt: str, tone: str = 'professional') -> str:
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
                logger.info(f"Section rewritten successfully (tone: {tone})")
                return rewritten
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit in rewrite (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return original_text
                time.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"Error in rewrite (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
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