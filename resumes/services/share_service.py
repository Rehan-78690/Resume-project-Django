import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from resumes.models import ShareLink

# Default share link expiry in days
DEFAULT_SHARE_DAYS = getattr(settings, 'DEFAULT_SHARE_DAYS', 30)

class ShareService:
    @staticmethod
    def create_link(user, resource_type, resource_id, expires_at=None):
        """
        Create or return existing active share link.
        Always sets default expiry if not provided.
        """
        # Set default expiry if not provided
        if expires_at is None:
            expires_at = timezone.now() + timedelta(days=DEFAULT_SHARE_DAYS)
        
        # Check for existing active link
        link = ShareLink.objects.filter(
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            is_active=True,
            revoked_at__isnull=True
        ).first()
        
        if link:
            # Check if existing link is expired
            if link.expires_at and link.expires_at < timezone.now():
                # Deactivate expired link
                link.is_active = False
                link.save(update_fields=['is_active'])
                link = None
        
        if not link:
            # Create new link
            token = secrets.token_urlsafe(32)
            link = ShareLink.objects.create(
                user=user,
                resource_type=resource_type,
                resource_id=resource_id,
                token=token,
                is_active=True,
                expires_at=expires_at
            )
        
        return link

    @staticmethod
    def revoke_link(user, resource_type, resource_id):
        """Revoke all active links for a resource."""
        links = ShareLink.objects.filter(
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            is_active=True
        )
        for link in links:
            link.is_active = False
            link.revoked_at = timezone.now()
            link.save(update_fields=['is_active', 'revoked_at'])

    @staticmethod
    def get_public_resource(token, resource_type):
        """
        Get share link for public access.
        Returns None if link doesn't exist, is inactive, or expired.
        """
        try:
            link = ShareLink.objects.get(
                token=token,
                resource_type=resource_type
            )
        except ShareLink.DoesNotExist:
            return None
        
        # Check if link is active
        if not link.is_active:
            return None
        
        # Check if link is expired
        if link.expires_at and link.expires_at <= timezone.now():
            return None
        
        # Update last accessed timestamp
        link.last_accessed_at = timezone.now()
        link.save(update_fields=['last_accessed_at'])
        
        return link
