from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from .serializers import ResumeUpdateSerializer


# Add this as a mixin or method to ResumeViewSet
class AutosaveMixin:
    @extend_schema(
        summary="Autosave resume (same as PATCH but dedicated endpoint)",
        request=ResumeUpdateSerializer
    )
    @action(detail=True, methods=['post'])
    def autosave(self, request, pk=None):
        """
        Dedicated autosave endpoint - functionally identical to PATCH.
        Provided for frontend convenience and semantic clarity.
        """
        resume = self.get_object()
        serializer = ResumeUpdateSerializer(
            resume,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            "success": True,
            "message": "Resume autosaved",
            "last_edited_at": resume.last_edited_at
        })
