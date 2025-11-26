# accounts/views.py
from django.contrib.auth import get_user_model

from rest_framework import permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema
from .social_serializers import GoogleAuthSerializer, FacebookAuthSerializer

from .models import EmailVerification
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    RegisterRequestSerializer,
    EmailRegisterInitiateSerializer,
    EmailRegisterVerifySerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()


@extend_schema(
    tags=["Auth"],
    summary="Login with email and password",
)
class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { "email": "...", "password": "..." }
    Returns: { "access", "refresh", "user": { ... } }
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=["Auth"],
    summary="Refresh access token",
)
class RefreshTokenView(TokenRefreshView):
    """
    POST /api/auth/refresh/
    Body: { "refresh": "..." }
    """
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=["Auth"],
    summary="Get current authenticated user",
)
class MeView(RetrieveAPIView):
    """
    GET /api/auth/me/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Auth"],
    summary="Logout (stateless)",
    description="Client should delete tokens; this endpoint just returns 204.",
)
class LogoutView(APIView):
    """
    POST /api/auth/logout/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # With token blacklisting, you would blacklist the refresh token here.
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    request=RegisterRequestSerializer,
    tags=["Auth"],
    summary="Register with email (2-step: send code + verify)",
    description=(
        "INIT STEP:\n"
        "- Body: {\"email\": \"...\", \"password\": \"...\"}\n"
        "- Sends verification code to email.\n\n"
        "VERIFY STEP:\n"
        "- Body: {\"email\": \"...\", \"code\": \"123456\"}\n"
        "- Creates user and returns JWT tokens."
    ),
)
class RegisterView(APIView):
    """
    POST /api/auth/register/
    Unified endpoint for registration:
    - INIT (email + password) -> 201, code sent.
    - VERIFY (email + code) -> 200, tokens + user.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        wrapper = RegisterRequestSerializer(data=request.data)
        wrapper.is_valid(raise_exception=True)
        data = wrapper.validated_data

        # VERIFY step
        if data.get("code"):
            return self._handle_verify(data)

        # INIT step
        return self._handle_init(data)

    def _handle_init(self, data):
        init_serializer = EmailRegisterInitiateSerializer(data=data)
        init_serializer.is_valid(raise_exception=True)
        record = init_serializer.save()

        return Response(
            {
                "detail": "Verification code sent to your email.",
                "email": record.email,
            },
            status=status.HTTP_201_CREATED,
        )

    def _handle_verify(self, data):
        verify_serializer = EmailRegisterVerifySerializer(data=data)
        verify_serializer.is_valid(raise_exception=True)
        record = verify_serializer.validated_data["record"]
        email = record.email

        # Create user with hashed password from verification record
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "role": record.role,
                "password": record.password_hash or "",  # set below if present
            },
        )

        # If we created the user, set password from hash
        if created and record.password_hash:
            user.password = record.password_hash
            user.save(update_fields=["password"])

        # Ensure user is not blocked or deactivated before issuing tokens
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")
        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed(
                "Your account has been blocked. Please contact support."
            )

        record.mark_used()

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
                "is_new": created,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=ForgotPasswordSerializer,
    tags=["Auth"],
    summary="Request password reset code",
)
class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/
    Always returns generic success message.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "If the email exists, a reset code has been sent.",
                "email": serializer.validated_data["email"],
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=ResetPasswordSerializer,
    tags=["Auth"],
    summary="Reset password using email + code",
)
class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Password has been reset successfully. You can now log in.",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=ChangePasswordSerializer,
    tags=["Auth"],
    summary="Change password (authenticated user)",
)
class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Auth"],
    summary="Deactivate (soft delete) account",
)
class DeactivateAccountView(APIView):
    """
    POST /api/auth/deactivate/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        user.deactivate()

        return Response(
            {"detail": "Your account has been deactivated."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Auth"],
    summary="Google login (placeholder)",
)
class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # TODO: verify Google ID token, then issue JWT
        return Response(
            {"detail": "Google login not implemented yet."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


@extend_schema(
    tags=["Auth"],
    summary="Facebook login (placeholder)",
)
class FacebookLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # TODO: verify Facebook access token, then issue JWT
        return Response(
            {"detail": "Facebook login not implemented yet."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
@extend_schema(
    tags=["Auth"],
    summary="Login / Register with Google",
    description="Accepts a Google access token and returns JWT tokens.",
    request=GoogleAuthSerializer,
)
class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        is_new = serializer.validated_data["is_new"]

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email
        refresh["auth_provider"] = user.auth_provider

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
                "is_new": is_new,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Auth"],
    summary="Login / Register with Facebook",
    description="Accepts a Facebook access token and returns JWT tokens.",
    request=FacebookAuthSerializer,
)
class FacebookLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = FacebookAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        is_new = serializer.validated_data["is_new"]

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email
        refresh["auth_provider"] = user.auth_provider

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
                "is_new": is_new,
            },
            status=status.HTTP_200_OK,
        )
