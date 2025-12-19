import secrets
from django.utils import timezone
from resumes.models import ShareLink
from django.shortcuts import get_object_or_404

class ShareService:
    @staticmethod
    def create_link(user, resource_type, resource_id):
        # Check existing active link
        link = ShareLink.objects.filter(
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            is_active=True,
            revoked_at__isnull=True
        ).first()
        
        if link:
            # Check expiry
            if link.expires_at and link.expires_at < timezone.now():
                link.is_active = False
                link.save()
            else:
                return link
                
        # Create new
        token = secrets.token_urlsafe(32)
        return ShareLink.objects.create(
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            token=token,
            is_active=True
        )

    @staticmethod
    def revoke_link(user, resource_type, resource_id):
        links = ShareLink.objects.filter(
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            is_active=True
        )
        for link in links:
            link.is_active = False
            link.revoked_at = timezone.now()
            link.save()

    @staticmethod
    def get_public_resource(token, resource_type):
        limit = timezone.now()
        link = ShareLink.objects.filter(
            token=token,
            resource_type=resource_type,
            is_active=True,
            revoked_at__isnull=True
        ).first()
        
        if not link:
            return None
            
        if link.expires_at and link.expires_at < limit:
            return None
            
        # Update accessed
        link.last_accessed_at = limit
        link.save(update_fields=['last_accessed_at'])
        
        return link
