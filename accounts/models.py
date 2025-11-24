from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"

    # We won’t use username for login; email will be unique identifier
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.USER,
    )

    # status / flags for future (block, soft delete, etc.)
    is_blocked = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # since email is the main field

    def __str__(self):
        return f"{self.email} ({self.role})"
