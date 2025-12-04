from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to allow only owners or admins to access objects.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is admin
        if request.user.role == User.Roles.ADMIN:
            return True
        
        # Check ownership for different object types
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'resume'):
            return obj.resume.user == request.user
        elif hasattr(obj, 'category'):
            return obj.category.resume.user == request.user
        elif hasattr(obj, 'section'):
            return obj.section.resume.user == request.user
        
        return False


class IsWizardOwner(permissions.BasePermission):
    """
    Permission to ensure users can only access their own wizard sessions.
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user