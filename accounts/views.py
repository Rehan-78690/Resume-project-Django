# accounts/views.py
from rest_framework import permissions
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
)


class RegisterView(CreateAPIView):
    """
    POST /api/auth/register/
    Body: { "email": "...", "password": "..." }
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { "email": "...", "password": "..." }
    Returns: { access, refresh, user: { ... } }
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RefreshTokenView(TokenRefreshView):
    """
    POST /api/auth/refresh/
    Body: { "refresh": "..." }
    """
    permission_classes = [permissions.AllowAny]


class MeView(RetrieveAPIView):
    """
    GET /api/auth/me/
    Returns the authenticated user's data.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    For pure JWT, logout is usually handled client-side
    (just delete tokens). Here we just return 204.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # If you later implement refresh token blacklisting,
        # you'll handle that here.
        return Response(status=204)


# OPTIONAL placeholders for Google/Facebook login – to be implemented next
class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # TODO: implement with allauth & Google access token
        return Response(
            {"detail": "Google login not implemented yet."},
            status=501,
        )


class FacebookLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # TODO: implement with allauth & Facebook access token
        return Response(
            {"detail": "Facebook login not implemented yet."},
            status=501,
        )
