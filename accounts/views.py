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
# Add to imports
from allauth.socialaccount.models import SocialAccount


@extend_schema(
    tags=["Profile"],
    summary="Get basic user profile info",
    description="Returns name, email, photo, and connected social providers for AI wizard."
)
class BasicProfileView(APIView):
    """
    GET /api/auth/profile/basic/
    Returns basic info for AI wizard prefill.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get connected social providers
        providers = list(
            SocialAccount.objects.filter(user=user)
            .values_list('provider', flat=True)
        )
        
        # Build name from first/last name or email
        name_parts = [user.first_name, user.last_name]
        name = " ".join([p for p in name_parts if p]).strip()
        if not name:
            name = user.email.split('@')[0]  # Fallback to email username
        
        return Response({
            "name": name,
            "email": user.email,
            "photo_url": user.avatar_url or "",
            "providers": providers,
            "has_google": "google" in providers,
            "has_facebook": "facebook" in providers
        })


@extend_schema(
    tags=["Profile"],
    summary="Get social import capabilities",
    description="Returns what data can be imported from connected social accounts."
)
class SocialImportSourcesView(APIView):
    """
    GET /api/auth/profile/import-sources/
    Returns social import capabilities.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check Google
        google_account = SocialAccount.objects.filter(
            user=user, provider='google'
        ).first()
        google_connected = bool(google_account)
        
        # Check Facebook
        facebook_account = SocialAccount.objects.filter(
            user=user, provider='facebook'
        ).first()
        facebook_connected = bool(facebook_account)
        
        return Response({
            "google": {
                "connected": google_connected,
                "can_import_name": google_connected,
                "can_import_photo": google_connected,
                "can_import_profile": False  # Phase 2
            },
            "facebook": {
                "connected": facebook_connected,
                "can_import_name": facebook_connected,
                "can_import_photo": facebook_connected,
                "can_import_profile": False  # Phase 2
            },
            "linkedin": {
                "connected": False,
                "can_import_name": False,
                "can_import_photo": False,
                "can_import_profile": False
            }
        })

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
