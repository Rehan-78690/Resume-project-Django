# accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone



class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Roles(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"

    class AuthProvider(models.TextChoices):
        EMAIL = "email", "Email"
        GOOGLE = "google", "Google"
        FACEBOOK = "facebook", "Facebook"

    username = None
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.USER,
    )

    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
    )

    is_blocked = models.BooleanField(default=False)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    # can be filled from Google/Facebook
    avatar_url = models.URLField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"

    def deactivate(self):
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.save(update_fields=["is_active", "deactivated_at"])

    def reactivate(self):
        self.is_active = True
        self.deactivated_at = None
        self.save(update_fields=["is_active", "deactivated_at"])


class EmailVerification(models.Model):
    """
    Used for:
    - Registration email verification (stores hashed password until verified)
    - Password reset codes (no password_hash needed)
    """

    class VerificationType(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        PASSWORD_RESET = "password_reset", "Password Reset"

    email = models.EmailField()
    password_hash = models.CharField(max_length=128, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=User.Roles.choices,
        default=User.Roles.USER,
    )
    code = models.CharField(max_length=6)  # "123456"
    verification_type = models.CharField(
        max_length=20,
        choices=VerificationType.choices,
        default=VerificationType.REGISTRATION,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        return f"{self.email} ({self.code}) - {self.verification_type}"

    class Meta:
        indexes = [
            models.Index(fields=["email", "code"]),
            models.Index(fields=["email", "verification_type", "is_used"]),
        ]
        verbose_name = "Email verification"
        verbose_name_plural = "Email verifications"
