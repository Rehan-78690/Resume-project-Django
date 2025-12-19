import abc
import os
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class PdfProvider(abc.ABC):
    @abc.abstractmethod
    def render_resume_to_pdf(self, resume, template_definition, options=None) -> bytes:
        pass

class PDFShiftProvider(PdfProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.pdfshift.io/v3/convert/pdf"

    def render_resume_to_pdf(self, resume, template_definition, options=None) -> bytes:
        # Placeholder: This would send HTML or URL to PDFShift
        # For now, we'll assume we send a raw HTML payload (constructed elsewhere) 
        # or a public URL if the resume has one.
        # Since we don't have HTML rendering logic here yet, we'll mock the request structure.
        
        # Real implementation would likely render the resume to HTML using Django templates
        # then send that HTML to the provider.
        
        # Checking if mocked for dev
        if settings.DEBUG and not self.api_key:
             return b"%PDF-1.4 Mock PDF"

        if not self.api_key:
            raise ValueError("PDFShift API key not configured")

        # In a real scenario, we would POST to the API
        # payload = {"source": html_content, "sandbox": True}
        # response = requests.post(self.api_url, auth=("api", self.api_key), json=payload)
        # return response.content
        
        return b"%PDF-1.4 Real PDF from PDFShift (Simulated)"

class CloudConvertProvider(PdfProvider):
    def __init__(self, api_key):
        self.api_key = api_key

    def render_resume_to_pdf(self, resume, template_definition, options=None) -> bytes:
        if settings.DEBUG and not self.api_key:
             return b"%PDF-1.4 Mock PDF"
        if not self.api_key:
             raise ValueError("CloudConvert API key not configured")
        
        return b"%PDF-1.4 Real PDF from CloudConvert (Simulated)"

class PdfService:
    def __init__(self):
        self.provider = self._get_provider()

    def _get_provider(self) -> PdfProvider:
        # Priority: PDFShift -> CloudConvert
        pdfshift_key = os.environ.get("PDFSHIFT_API_KEY")
        if pdfshift_key:
            return PDFShiftProvider(pdfshift_key)
        
        cloudconvert_key = os.environ.get("CLOUDCONVERT_API_KEY")
        if cloudconvert_key:
            return CloudConvertProvider(cloudconvert_key)
            
        return None

    def generate_pdf(self, resume) -> bytes:
        if not self.provider:
            # Fallback for dev without keys or error
            if settings.DEBUG:
                logger.warning("No PDF provider configured, returning mock PDF")
                return b"%PDF-1.4 Mock PDF (No Provider)"
            raise ValueError("PDF provider not configured")
            
        # Todo: Render resume to HTML string here?
        # html = render_to_string('resumes/pdf_template.html', {'resume': resume})
        # For now, passing mock objects
        return self.provider.render_resume_to_pdf(resume, {})
    
    def generate_cover_letter_pdf(self, cover_letter) -> bytes:
        """Generate PDF for a cover letter."""
        if not self.provider:
            if settings.DEBUG:
                logger.warning("No PDF provider configured, returning mock CL PDF")
                return b"%PDF-1.4 Mock Cover Letter PDF (No Provider)"
            raise ValueError("PDF provider not configured")
            
        # Todo: Render cover letter to HTML
        # Use cover_letter.template.definition if available
        # html = render_to_string('cover_letters/pdf_template.html', {'cover_letter': cover_letter})
        return self.provider.render_resume_to_pdf(cover_letter, {})
