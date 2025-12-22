# resumes/admin.py
import csv
import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Template,
    Resume,
    PersonalInfo,
    WorkExperience,
    Education,
    SkillCategory,
    SkillItem,
    Strength,
    Hobby,
    CustomSection,
    CustomItem,
    ResumeWizardSession,
    ShareLink,
    ResumeVersion,
)


# -------------------------
# Helpers / Filters / Exports
# -------------------------
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


class DateRangeFilter(SimpleListFilter):
    title = "created range"
    parameter_name = "created_range"

    def lookups(self, request, model_admin):
        return (("today", "Today"), ("7d", "Last 7 days"), ("30d", "Last 30 days"))

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "today":
            return queryset.filter(created_at__date=now.date())
        if self.value() == "7d":
            return queryset.filter(created_at__gte=now - timedelta(days=7))
        if self.value() == "30d":
            return queryset.filter(created_at__gte=now - timedelta(days=30))
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
            val = getattr(obj, f.name)
            row[f.name] = str(val) if hasattr(val, "hex") else val
        data.append(row)

    response = HttpResponse(json.dumps(data, indent=2, default=str), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{modeladmin.model._meta.model_name}.json"'
    return response


export_as_csv.short_description = "Export selected as CSV"
export_as_json.short_description = "Export selected as JSON"


# -------------------------
# Inlines
# -------------------------
class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    extra = 0
    can_delete = False


class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 0
    fields = ("position_title", "company_name", "start_date", "end_date", "is_current", "order")
    ordering = ("order",)


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0
    fields = ("degree", "school_name", "start_date", "end_date", "is_current", "order")
    ordering = ("order",)


class SkillItemInline(admin.TabularInline):
    model = SkillItem
    extra = 0
    fields = ("name", "level", "order")
    ordering = ("order",)


class CustomItemInline(admin.TabularInline):
    model = CustomItem
    extra = 0
    fields = ("title", "subtitle", "meta", "start_date", "end_date", "is_current", "order")
    ordering = ("order",)


# -------------------------
# Template Admin
# -------------------------
@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_active", "is_premium", "usage_count", "updated_at")
    list_filter = ("is_active", "is_premium", "category", DateRangeFilter)
    search_fields = ("id", "name", "slug", "category", "description")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "usage_count", "definition_preview")
    actions = [
        "activate_templates", "deactivate_templates",
        "mark_premium", "mark_free",
        export_as_csv, export_as_json
    ]

    fieldsets = (
        ("Basic", {"fields": ("id", "name", "slug", "description", "category")}),
        ("Availability", {"fields": ("is_active", "is_premium", "preview_image_url")}),
        ("Definition", {"fields": ("definition", "definition_preview"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_resume_count=Count("resume"))

    def usage_count(self, obj):
        return getattr(obj, "_resume_count", 0)
    usage_count.short_description = "Resumes using this"
    usage_count.admin_order_field = "_resume_count"

    def definition_preview(self, obj):
        try:
            return format_html(
                "<pre style='max-height:300px;overflow:auto'>{}</pre>",
                json.dumps(obj.definition or {}, indent=2)
            )
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


# -------------------------
# Resume Admin
# -------------------------
@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = (
        "title", "user_email", "status_badge", "template",
        "language", "ai_badge", "updated_at", "deleted_badge"
    )
    list_filter = (DeletedFilter, "status", "language", "template", "is_ai_generated", DateRangeFilter)
    search_fields = ("title", "user__email", "target_role", "slug", "user__first_name", "user__last_name")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "slug", "created_at", "updated_at", "last_edited_at", "deleted_at", "share_links_preview")
    fieldsets = (
        ("Basic Info", {"fields": ("user", "title", "slug", "target_role")}),
        ("Styling", {"fields": ("template", "language", "section_settings")}),
        ("AI Metadata", {"fields": ("is_ai_generated", "ai_model", "ai_prompt"), "classes": ("collapse",)}),
        ("Status / Timestamps", {"fields": ("status", "created_at", "updated_at", "last_edited_at", "deleted_at")}),
        ("Sharing", {"fields": ("share_links_preview",), "classes": ("collapse",)}),
    )
    inlines = [PersonalInfoInline, WorkExperienceInline, EducationInline]
    actions = [
        "publish_resumes", "archive_resumes",
        "soft_delete_resumes", "restore_resumes",
        export_as_csv, export_as_json,
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "template").prefetch_related(
            "work_experiences", "educations", "skill_categories", "strengths", "hobbies", "custom_sections"
        )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"

    def status_badge(self, obj):
        color = {"draft": "#6b7280", "published": "#16a34a", "archived": "#f59e0b"}.get(obj.status, "#3b82f6")
        return format_html(
            "<span style='padding:2px 8px;border-radius:10px;background:{};color:#fff;font-size:12px'>{}</span>",
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def ai_badge(self, obj):
        if obj.is_ai_generated:
            return format_html("<span style='padding:2px 8px;border-radius:10px;background:#7c3aed;color:#fff;font-size:12px'>AI</span>")
        return ""
    ai_badge.short_description = "AI"

    def deleted_badge(self, obj):
        if obj.deleted_at:
            return format_html("<span style='padding:2px 8px;border-radius:10px;background:#dc2626;color:#fff;font-size:12px'>Deleted</span>")
        return ""
    deleted_badge.short_description = "Deleted"

    def share_links_preview(self, obj):
        links = ShareLink.objects.filter(resource_type="resume", resource_id=obj.id).order_by("-created_at")[:10]
        if not links:
            return "No share links."
        rows = []
        for l in links:
            status = "Active" if l.is_active else "Revoked"
            expires = l.expires_at.strftime("%Y-%m-%d") if l.expires_at else "Never"
            # Keep URL relative to avoid environment mismatch
            url = f"/api/public/r/{l.token}/"
            rows.append(f"{status} • expires: {expires} • {url}")
        return format_html("<pre style='max-height:220px;overflow:auto'>{}</pre>", "\n".join(rows))
    share_links_preview.short_description = "Share Links (latest 10)"

    @admin.action(description="Publish selected resumes")
    def publish_resumes(self, request, queryset):
        queryset.update(status=Resume.Status.PUBLISHED)

    @admin.action(description="Archive selected resumes")
    def archive_resumes(self, request, queryset):
        queryset.update(status=Resume.Status.ARCHIVED)

    @admin.action(description="Soft delete selected resumes")
    def soft_delete_resumes(self, request, queryset):
        for r in queryset:
            r.soft_delete()

    @admin.action(description="Restore selected resumes (clear deleted_at)")
    def restore_resumes(self, request, queryset):
        queryset.update(deleted_at=None)


# -------------------------
# PersonalInfo / Skills / Custom Sections
# -------------------------
@admin.register(PersonalInfo)
class PersonalInfoAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "city", "country", "resume")
    search_fields = ("first_name", "last_name", "email", "resume__title", "resume__user__email")
    ordering = ("-id",)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "resume", "order")
    search_fields = ("name", "resume__title", "resume__user__email")
    inlines = [SkillItemInline]
    ordering = ("resume", "order")
    actions = [export_as_csv, export_as_json]


@admin.register(Strength)
class StrengthAdmin(admin.ModelAdmin):
    list_display = ("label", "resume", "order")
    search_fields = ("label", "resume__title", "resume__user__email")
    ordering = ("resume", "order")
    actions = [export_as_csv, export_as_json]


@admin.register(Hobby)
class HobbyAdmin(admin.ModelAdmin):
    list_display = ("label", "resume", "order")
    search_fields = ("label", "resume__title", "resume__user__email")
    ordering = ("resume", "order")
    actions = [export_as_csv, export_as_json]


@admin.register(CustomSection)
class CustomSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "resume", "order")
    list_filter = ("type",)
    search_fields = ("title", "resume__title", "resume__user__email")
    inlines = [CustomItemInline]
    ordering = ("resume", "order")
    actions = [export_as_csv, export_as_json]


# -------------------------
# Wizard / ShareLink / Versions
# -------------------------
@admin.register(ResumeWizardSession)
class ResumeWizardSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "consumed", "expired_flag")
    list_filter = ("consumed", "created_at", DateRangeFilter)
    readonly_fields = ("id", "created_at", "input_preview", "draft_preview")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    actions = [export_as_csv, export_as_json]

    def expired_flag(self, obj):
        return obj.is_expired()
    expired_flag.boolean = True
    expired_flag.short_description = "Expired?"

    def input_preview(self, obj):
        return format_html("<pre style='max-height:260px;overflow:auto'>{}</pre>", json.dumps(obj.input_payload, indent=2))
    input_preview.short_description = "Input JSON"

    def draft_preview(self, obj):
        return format_html("<pre style='max-height:260px;overflow:auto'>{}</pre>", json.dumps(obj.draft_payload, indent=2))
    draft_preview.short_description = "Draft JSON"


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "resource_type", "resource_id", "is_active", "expires_at", "created_at", "last_accessed_at", "revoked_at")
    list_filter = ("resource_type", "is_active", "created_at", DateRangeFilter)
    search_fields = ("user__email", "token", "resource_id")
    readonly_fields = ("id", "created_at", "last_accessed_at", "revoked_at", "open_url")
    ordering = ("-created_at",)
    actions = ["revoke_links", "activate_links", "extend_7_days", export_as_csv, export_as_json]

    def open_url(self, obj):
        url = f"/api/public/r/{obj.token}/"
        return format_html("<a href='{}' target='_blank'>{}</a>", url, url)
    open_url.short_description = "Open Public URL"

    @admin.action(description="Revoke selected links")
    def revoke_links(self, request, queryset):
        queryset.update(is_active=False, revoked_at=timezone.now())

    @admin.action(description="Activate selected links (clears revoked_at)")
    def activate_links(self, request, queryset):
        queryset.update(is_active=True, revoked_at=None)

    @admin.action(description="Extend expiry by 7 days (only those with expires_at set)")
    def extend_7_days(self, request, queryset):
        for link in queryset.exclude(expires_at__isnull=True):
            link.expires_at = link.expires_at + timedelta(days=7)
            link.save(update_fields=["expires_at"])


@admin.register(ResumeVersion)
class ResumeVersionAdmin(admin.ModelAdmin):
    list_display = ("resume", "version_number", "created_at", "created_by")
    list_filter = ("created_at", DateRangeFilter)
    search_fields = ("resume__title", "created_by__email")
    readonly_fields = ("id", "created_at", "snapshot_preview")
    ordering = ("-created_at",)
    actions = [export_as_csv, export_as_json]

    def snapshot_preview(self, obj):
        return format_html("<pre style='max-height:380px;overflow:auto'>{}</pre>", json.dumps(obj.snapshot_data, indent=2))
    snapshot_preview.short_description = "Snapshot JSON"
