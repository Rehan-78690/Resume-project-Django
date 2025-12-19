from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from resumes.models import Template
from ai_core.models import AIUsageLog
from resumes.serializers import TemplateSerializer
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class AdminUserSerializer:
    """Serializer for user data in admin panel"""
    from rest_framework import serializers
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'date_joined',
            'last_login'
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'last_login']


# Import serializers properly
from rest_framework import serializers

class AdminUserListSerializer(serializers.ModelSerializer):
    resume_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'date_joined',
            'last_login', 'resume_count'
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'last_login']


class AdminUserDetailSerializer(serializers.ModelSerializer):
    resume_count = serializers.IntegerField(read_only=True)
    cover_letter_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
            'resume_count', 'cover_letter_count'
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'last_login', 'resume_count', 'cover_letter_count']


class AIUsageLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AIUsageLog
        fields = [
            'id', 'user', 'user_email', 'feature_type',
            'model_name', 'tokens_in', 'tokens_out',
            'cost_estimate', 'success', 'created_at'
        ]


@extend_schema(tags=['admin'])
class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AdminUserListSerializer
        return AdminUserDetailSerializer
    
    def get_queryset(self):
        queryset = User.objects.annotate(
            resume_count=Count('resumes', filter=Q(resumes__deleted_at__isnull=True))
        )
        
        # Add cover letter count if available
        try:
            from cover_letters.models import CoverLetter
            queryset = queryset.annotate(
                cover_letter_count=Count('cover_letters', filter=Q(cover_letters__deleted_at__isnull=True))
            )
        except:
            pass
            
        return queryset
    
    @extend_schema(
        summary="Block/unblock user",
        request={"is_active": serializers.BooleanField()}
    )
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({
            "id": str(user.id),
            "is_active": user.is_active
        })


@extend_schema(tags=['admin'])
class AdminTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = TemplateSerializer
    queryset = Template.objects.all()
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        template = self.get_object()
        template.is_active = not template.is_active
        template.save(update_fields=['is_active'])
        return Response(TemplateSerializer(template).data)


@extend_schema(tags=['admin'])
class AdminAILogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AIUsageLogSerializer
    queryset = AIUsageLog.objects.select_related('user').all()
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Filter by feature type
        feature_type = self.request.query_params.get('feature_type')
        if feature_type:
            queryset = queryset.filter(feature_type=feature_type)
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by success status
        success = self.request.query_params.get('success')
        if success is not None:
            queryset = queryset.filter(success=success.lower() == 'true')
        
        return queryset


@extend_schema(tags=['admin'])
class AdminCoverLetterTemplateViewSet(viewsets.ModelViewSet):
    """Admin viewset for managing cover letter templates."""
    permission_classes = [IsAdminUser]
    queryset = None
    serializer_class = None
    ordering = ['-created_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import here to avoid circular import
        from cover_letters.models import CoverLetterTemplate
        from cover_letters.serializers import CoverLetterTemplateSerializer
        self.queryset = CoverLetterTemplate.objects.all()
        self.serializer_class = CoverLetterTemplateSerializer
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle template active status."""
        template = self.get_object()
        template.is_active = not template.is_active
        template.save(update_fields=['is_active'])
        return Response(self.get_serializer(template).data)

