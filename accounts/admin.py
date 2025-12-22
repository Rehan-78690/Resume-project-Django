# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django import forms
from django.utils import timezone

from .models import EmailVerification

User = get_user_model()


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role", "auth_provider", "is_active", "is_staff", "is_superuser")

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "email", "first_name", "last_name",
        "role", "auth_provider",
        "is_active", "is_staff", "is_superuser",
        "is_blocked", "deactivated_at",
        "date_joined", "last_login",
    )
    list_filter = (
        "role", "auth_provider",
        "is_active", "is_staff", "is_superuser",
        "is_blocked",
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "deactivated_at")

    fieldsets = (
        ("Account", {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "avatar_url")}),
        ("Access / Role", {"fields": ("role", "auth_provider", "is_blocked")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("date_joined", "last_login", "deactivated_at")}),
    )

    add_fieldsets = (
        ("Create User", {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "auth_provider",
                       "password1", "password2", "is_active", "is_staff", "is_superuser"),
        }),
    )

    # Your user has username=None, this avoids BaseUserAdmin assumptions
    username_field = None

    actions = [
        "make_staff", "remove_staff",
        "make_superuser", "remove_superuser",
        "set_role_admin", "set_role_user",
        "block_users", "unblock_users",
        "deactivate_users", "reactivate_users",
    ]

    @admin.action(description="Make selected users STAFF")
    def make_staff(self, request, queryset):
        queryset.update(is_staff=True)

    @admin.action(description="Remove STAFF from selected users")
    def remove_staff(self, request, queryset):
        queryset.update(is_staff=False)

    @admin.action(description="Make selected users SUPERUSER")
    def make_superuser(self, request, queryset):
        queryset.update(is_superuser=True, is_staff=True)

    @admin.action(description="Remove SUPERUSER from selected users")
    def remove_superuser(self, request, queryset):
        queryset.update(is_superuser=False)

    @admin.action(description="Set role = ADMIN (does NOT auto grant staff)")
    def set_role_admin(self, request, queryset):
        queryset.update(role=User.Roles.ADMIN)

    @admin.action(description="Set role = USER")
    def set_role_user(self, request, queryset):
        queryset.update(role=User.Roles.USER)

    @admin.action(description="Block selected users")
    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)

    @admin.action(description="Unblock selected users")
    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False)

    @admin.action(description="Deactivate selected users (sets deactivated_at)")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False, deactivated_at=timezone.now())

    @admin.action(description="Reactivate selected users (clears deactivated_at)")
    def reactivate_users(self, request, queryset):
        queryset.update(is_active=True, deactivated_at=None)


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("email", "verification_type", "code", "role", "is_used", "created_at", "expires_at")
    list_filter = ("verification_type", "role", "is_used", "created_at")
    search_fields = ("email", "code")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    actions = ["mark_used"]

    @admin.action(description="Mark selected verifications as USED")
    def mark_used(self, request, queryset):
        queryset.update(is_used=True)
