# accounts/serializers.py
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.utils import timezone
from datetime import timedelta
import random

from .models import EmailVerification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role", "is_blocked", "is_active","auth_provider","avatar_url"]
        read_only_fields = ["id", "role", "is_blocked", "is_active","auth_provider","avatar_url"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom login:
    - Same error for email-not-found & wrong-password for security.
    - Check is_active + is_blocked.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid email or password")

        if not user.check_password(password):
            raise AuthenticationFailed("Invalid email or password")

        if not user.is_active:
            raise AuthenticationFailed(
                "Your account has been deactivated. Please contact support."
            )

        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed(
                "Your account has been blocked. Please contact support."
            )

        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }
        return data


class RegisterRequestSerializer(serializers.Serializer):
    """
    Unified register request:
    - INIT:   { "email": "...", "password": "..." }
    - VERIFY: { "email": "...", "code": "123456" }
    """
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, min_length=8, required=False
    )
    code = serializers.CharField(
        max_length=6, required=False
    )

    def validate(self, attrs):
        password = attrs.get("password")
        code = attrs.get("code")

        if bool(password) == bool(code):
            raise ValidationError(
                "Provide either password (init) OR code (verify), not both."
            )

        return attrs


class EmailRegisterInitiateSerializer(serializers.Serializer):
    """
    Step 1 (INIT): user sends email + password.
    We:
      - ensure user doesn't exist
      - create EmailVerification with hashed password
      - send 6-digit code
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]

        # Clean old unused registration codes
        EmailVerification.objects.filter(
            email=email,
            is_used=False,
            verification_type=EmailVerification.VerificationType.REGISTRATION,
        ).delete()

        code = f"{random.randint(0, 999999):06d}"
        password_hash = make_password(password)
        expires_at = timezone.now() + timedelta(minutes=10)

        record = EmailVerification.objects.create(
            email=email,
            password_hash=password_hash,
            role=User.Roles.USER,
            code=code,
            verification_type=EmailVerification.VerificationType.REGISTRATION,
            expires_at=expires_at,
        )

        self._send_verification_email(email, code)
        return record

    def _send_verification_email(self, email, code):
        subject = "Verify your email"
        message = f"""
        Hello,

        Your verification code is: {code}

        This code will expire in 10 minutes.

        If you didn't request this, you can ignore this email.

        Best regards,
        Resume Builder Team
        """
        send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )


class EmailRegisterVerifySerializer(serializers.Serializer):
    """
    Step 2 (VERIFY): user sends email + code.
    We:
      - validate that a non-used, non-expired REGISTRATION record exists
      - attach it as 'record' in validated_data
    """
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs.get("email")
        code = attrs.get("code")

        try:
            record = EmailVerification.objects.filter(
                email=email,
                code=code,
                is_used=False,
                verification_type=EmailVerification.VerificationType.REGISTRATION,
            ).latest("created_at")
        except EmailVerification.DoesNotExist:
            raise ValidationError("Invalid verification code.")

        if record.is_expired():
            raise ValidationError("Verification code has expired.")

        attrs["record"] = record
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Initiate password reset.
    Always returns success message (even if email not found or inactive).
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        # Don't leak if user exists or not
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            # Silent success
            return {"email": email}

        EmailVerification.objects.filter(
            email=email,
            is_used=False,
            verification_type=EmailVerification.VerificationType.PASSWORD_RESET,
        ).delete()

        code = f"{random.randint(0, 999999):06d}"
        expires_at = timezone.now() + timedelta(minutes=15)

        record = EmailVerification.objects.create(
            email=email,
            code=code,
            verification_type=EmailVerification.VerificationType.PASSWORD_RESET,
            expires_at=expires_at,
        )

        self._send_reset_email(email, code)
        return record

    def _send_reset_email(self, email, code):
        subject = "Password reset request"
        message = f"""
        Hello,

        You requested a password reset. Your reset code is: {code}

        This code will expire in 15 minutes.

        If you didn't request a password reset, you can ignore this email.

        Best regards,
        Resume Builder Team
        """
        send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )


class ResetPasswordSerializer(serializers.Serializer):
    """
    Complete password reset: email + code + new_password
    """
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = attrs.get("email")
        code = attrs.get("code")
        new_password = attrs.get("new_password")

        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            # generic error, don't leak details
            raise ValidationError("Invalid reset request.")

        try:
            record = EmailVerification.objects.filter(
                email=email,
                code=code,
                is_used=False,
                verification_type=EmailVerification.VerificationType.PASSWORD_RESET,
            ).latest("created_at")
        except EmailVerification.DoesNotExist:
            raise ValidationError("Invalid reset code.")

        if record.is_expired():
            raise ValidationError("Reset code has expired.")

        validate_password(new_password)

        attrs["user"] = user
        attrs["record"] = record
        return attrs

    def save(self):
        user = self.validated_data["user"]
        record = self.validated_data["record"]
        new_password = self.validated_data["new_password"]

        user.set_password(new_password)
        user.save()

        record.mark_used()

        # Clean other unused reset codes for this email
        EmailVerification.objects.filter(
            email=user.email,
            is_used=False,
            verification_type=EmailVerification.VerificationType.PASSWORD_RESET,
        ).delete()


class ChangePasswordSerializer(serializers.Serializer):
    """
    Change password for authenticated users.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def save(self):
        user = self.context["request"].user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
