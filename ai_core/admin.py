from django.contrib import admin
from .models import AIUsageLog

@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'feature_type', 'model_name', 'success', 'tokens_in', 'tokens_out', 'created_at']
    list_filter = ['feature_type', 'success', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
