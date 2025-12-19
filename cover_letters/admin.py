from django.contrib import admin
from .models import CoverLetter

@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'company_name', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'user__email', 'company_name', 'job_title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted_at__isnull=True)
