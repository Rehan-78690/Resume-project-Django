# ai_core/admin.py
import csv
import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Sum

from .models import AIUsageLog


class SuccessFilter(SimpleListFilter):
    title = "success"
    parameter_name = "success_state"

    def lookups(self, request, model_admin):
        return (("yes", "Successful"), ("no", "Failed"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(success=True)
        if self.value() == "no":
            return queryset.filter(success=False)
        return queryset


def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ai_usage_logs.csv"'
    writer = csv.writer(response)
    writer.writerow(["user", "feature_type", "model_name", "tokens_in", "tokens_out", "cost_estimate", "success", "created_at"])
    for log in queryset.select_related("user"):
        writer.writerow([log.user.email, log.feature_type, log.model_name, log.tokens_in, log.tokens_out, log.cost_estimate, log.success, log.created_at])
    return response


def export_as_json(modeladmin, request, queryset):
    data = []
    for log in queryset.select_related("user"):
        data.append({
            "id": str(log.id),
            "user": log.user.email,
            "feature_type": log.feature_type,
            "model_name": log.model_name,
            "tokens_in": log.tokens_in,
            "tokens_out": log.tokens_out,
            "cost_estimate": str(log.cost_estimate),
            "success": log.success,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat(),
        })
    response = HttpResponse(json.dumps(data, indent=2), content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="ai_usage_logs.json"'
    return response


export_as_csv.short_description = "Export selected as CSV"
export_as_json.short_description = "Export selected as JSON"


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ("user_email", "feature_badge", "model_name", "tokens_total", "cost_estimate", "success_badge", "created_at")
    list_filter = (SuccessFilter, "feature_type", "model_name", "created_at")
    search_fields = ("user__email", "feature_type", "model_name", "error_message")
    readonly_fields = ("created_at", "tokens_total", "error_preview")
    ordering = ("-created_at",)
    actions = [export_as_csv, export_as_json, "show_month_cost"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"

    def tokens_total(self, obj):
        return (obj.tokens_in or 0) + (obj.tokens_out or 0)
    tokens_total.short_description = "Total tokens"

    def success_badge(self, obj):
        return format_html("<b style='color:{}'>{}</b>", "#16a34a" if obj.success else "#dc2626", "✓" if obj.success else "✗")
    success_badge.short_description = "OK?"

    def feature_badge(self, obj):
        return format_html("<span style='padding:2px 8px;border-radius:10px;background:#0ea5e9;color:#fff;font-size:12px'>{}</span>", obj.get_feature_type_display())
    feature_badge.short_description = "Feature"

    def error_preview(self, obj):
        if not obj.error_message:
            return "No error"
        return format_html("<pre style='max-height:240px;overflow:auto;background:#fee2e2;padding:10px;border-radius:6px'>{}</pre>", obj.error_message)
    error_preview.short_description = "Error message"

    @admin.action(description="Show total cost for current month (selected or all)")
    def show_month_cost(self, request, queryset):
        now = timezone.now()
        base = queryset if queryset.exists() else AIUsageLog.objects.all()
        total = base.filter(created_at__year=now.year, created_at__month=now.month).aggregate(s=Sum("cost_estimate"))["s"] or 0
        self.message_user(request, f"Total AI cost for {now.strftime('%B %Y')}: {total}")
