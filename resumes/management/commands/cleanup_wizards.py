from django.core.management.base import BaseCommand
from django.utils import timezone
from resumes.models import ResumeWizardSession


class Command(BaseCommand):
    help = 'Clean up expired wizard sessions'
    
    def handle(self, *args, **options):
        expired_count = ResumeWizardSession.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {expired_count} expired wizard sessions')
        )