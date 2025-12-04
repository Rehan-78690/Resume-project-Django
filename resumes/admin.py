from django.contrib import admin
from .models import (
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
)

# ===== Inlines =====


class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class SkillItemInline(admin.TabularInline):
    model = SkillItem
    extra = 0


class CustomItemInline(admin.TabularInline):
    model = CustomItem
    extra = 0


# ===== Main Admins =====


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "status", "template_id", "is_ai_generated", "created_at"]
    list_filter = ["status", "template_id", "is_ai_generated", "language"]
    search_fields = ["title", "user__email", "target_role", "slug"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]
    fieldsets = (
        ("Basic Info", {"fields": ("user", "title", "slug", "target_role")}),
        ("Styling", {"fields": ("template_id", "language")}),
        ("AI Metadata", {"fields": ("is_ai_generated", "ai_model", "ai_prompt")}),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "created_at",
                    "updated_at",
                    "last_edited_at",
                    "deleted_at",
                )
            },
        ),
    )
    # ✅ WorkExperience & Education belong to Resume, so inlines go here:
    inlines = [WorkExperienceInline, EducationInline]


@admin.register(PersonalInfo)
class PersonalInfoAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "email", "city", "country", "resume"]
    search_fields = ["first_name", "last_name", "email", "resume__title"]
    # ❌ no inlines here, models don't FK PersonalInfo


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "resume", "order"]
    search_fields = ["name", "resume__title"]
    inlines = [SkillItemInline]


@admin.register(Strength)
class StrengthAdmin(admin.ModelAdmin):
    list_display = ["label", "resume", "order"]
    search_fields = ["label", "resume__title"]


@admin.register(Hobby)
class HobbyAdmin(admin.ModelAdmin):
    list_display = ["label", "resume", "order"]
    search_fields = ["label", "resume__title"]


@admin.register(CustomSection)
class CustomSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "resume", "order"]
    list_filter = ["type"]
    search_fields = ["title", "resume__title"]
    inlines = [CustomItemInline]


@admin.register(ResumeWizardSession)
class ResumeWizardSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "consumed"]
    list_filter = ["consumed"]
    readonly_fields = ["id", "created_at"]
    search_fields = ["user__email"]
