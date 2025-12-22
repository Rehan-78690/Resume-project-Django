# cover_letters/admin.py
import csv
import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Count

from .models import CoverLetter, CoverLetterTemplate


class DeletedFilter(SimpleListFilter):
    title = "deletion status"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (("active", "Active"), ("deleted", "Deleted"))

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset


def export_as_csv(modeladmin, request, queryset):
    model = modeladmin.model
    meta = model._meta
    field_names = [f.name for f in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{meta.model_name}.csv"'
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])
    return response


def export_as_json(modeladmin, request, queryset):
    data = []
    for obj in queryset:
        row = {}
        for f in obj._meta.fields:
            row[f.name] = str(getattr(obj, f.name))
        data.append(row)
    response = HttpResponse(json.dumps(data, indent=2, default=str), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{modeladmin.model._meta.model_name}.json"'
    return response


export_as_csv.short_description = "Export selected as CSV"
export_as_json.short_description = "Export selected as JSON"


@admin.register(CoverLetterTemplate)
class CoverLetterTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_active", "is_premium", "usage_count", "updated_at")
    list_filter = ("is_active", "is_premium", "category")
    search_fields = ("id", "name", "slug", "category")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "usage_count", "definition_preview")
    actions = ["activate_templates", "deactivate_templates", "mark_premium", "mark_free", export_as_csv, export_as_json]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_cl_count=Count("coverletter"))

    def usage_count(self, obj):
        return getattr(obj, "_cl_count", 0)
    usage_count.short_description = "Cover letters using this"
    usage_count.admin_order_field = "_cl_count"

    def definition_preview(self, obj):
        try:
            return format_html("<pre style='max-height:300px;overflow:auto'>{}</pre>", json.dumps(obj.definition or {}, indent=2))
        except Exception:
            return "Invalid JSON"
    definition_preview.short_description = "Definition (readable)"

    @admin.action(description="Activate selected templates")
    def activate_templates(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected templates")
    def deactivate_templates(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Mark selected templates as PREMIUM")
    def mark_premium(self, request, queryset):
        queryset.update(is_premium=True)

    @admin.action(description="Mark selected templates as FREE")
    def mark_free(self, request, queryset):
        queryset.update(is_premium=False)


@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ("title", "user_email", "company_name", "job_title", "status_badge", "template", "updated_at", "deleted_badge")
    list_filter = (DeletedFilter, "status", "template", "created_at")
    search_fields = ("title", "user__email", "company_name", "job_title")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "body_preview")
    fieldsets = (
        ("Basic Info", {"fields": ("user", "linked_resume", "title")}),
        ("Job Details", {"fields": ("company_name", "job_title", "job_description")}),
        ("Content", {"fields": ("template", "body", "body_preview")}),
        ("Status / Timestamps", {"fields": ("status", "created_at", "updated_at", "deleted_at")}),
    )

    actions = ["publish_letters", "draft_letters", "soft_delete_letters", "restore_letters", export_as_csv, export_as_json]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "template", "linked_resume")

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"

    def status_badge(self, obj):
        color = {"draft": "#6b7280", "published": "#16a34a"}.get(obj.status, "#3b82f6")
        return format_html("<span style='padding:2px 8px;border-radius:10px;background:{};color:#fff;font-size:12px'>{}</span>", color, obj.get_status_display())
    status_badge.short_description = "Status"

    def deleted_badge(self, obj):
        if obj.deleted_at:
            return format_html("<span style='padding:2px 8px;border-radius:10px;background:#dc2626;color:#fff;font-size:12px'>Deleted</span>")
        return ""
    deleted_badge.short_description = "Deleted"

    def body_preview(self, obj):
        text = obj.body or ""
        preview = text[:800] + ("..." if len(text) > 800 else "")
        return format_html("<div style='max-height:260px;overflow:auto;white-space:pre-wrap;background:#f3f4f6;padding:10px;border-radius:6px'>{}</div>", preview)
    body_preview.short_description = "Body preview"

    @admin.action(description="Publish selected cover letters")
    def publish_letters(self, request, queryset):
        queryset.update(status="published")

    @admin.action(description="Set selected cover letters to draft")
    def draft_letters(self, request, queryset):
        queryset.update(status="draft")

    @admin.action(description="Soft delete selected cover letters")
    def soft_delete_letters(self, request, queryset):
        for c in queryset:
            c.soft_delete()

    @admin.action(description="Restore selected cover letters")
    def restore_letters(self, request, queryset):
        queryset.update(deleted_at=None)
