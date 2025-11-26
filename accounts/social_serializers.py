# accounts/social_serializers.py
import requests
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from allauth.socialaccount.models import SocialAccount

User = get_user_model()


class BaseSocialSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=True)

    provider_name = None  # override in subclasses

    def get_or_create_social_user(self, email, uid, defaults):
        """
        Use allauth's SocialAccount to link provider account <-> User.
        """
        user, created_user = User.objects.get_or_create(
            email=email,
            defaults=defaults,
        )

        # Ensure we record provider
        if self.provider_name == "google":
            user.auth_provider = User.AuthProvider.GOOGLE
        elif self.provider_name == "facebook":
            user.auth_provider = User.AuthProvider.FACEBOOK
        user.save()

        # Create or get SocialAccount entry
        social, created_social = SocialAccount.objects.get_or_create(
            user=user,
            provider=self.provider_name,
            uid=uid,
        )

        return user, (created_user or created_social)


class GoogleAuthSerializer(BaseSocialSerializer):
    """
    Accepts a Google access_token (or id_token if you adjust the URL) from frontend,
    verifies it with Google, then links/creates a user + SocialAccount.
    """
    provider_name = "google"

    def validate(self, attrs):
        token = attrs["access_token"]

        # Call Google userinfo endpoint
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            params={"access_token": token},
            timeout=5,
        )
        if resp.status_code != 200:
            raise ValidationError("Invalid Google access token.")

        data = resp.json()
        email = data.get("email")
        email_verified = data.get("email_verified")
        sub = data.get("sub")  # unique id for Google user

        if not email or not email_verified:
            raise ValidationError("Google email not verified.")

        defaults = {
            "first_name": data.get("given_name", ""),
            "last_name": data.get("family_name", ""),
            "avatar_url": data.get("picture", ""),
        }

        user, is_new = self.get_or_create_social_user(
            email=email,
            uid=sub,
            defaults=defaults,
        )

        if not user.is_active:
            raise AuthenticationFailed("Account deactivated. Please contact support.")

        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed("Account blocked. Please contact support.")

        attrs["user"] = user
        attrs["is_new"] = is_new
        return attrs


class FacebookAuthSerializer(BaseSocialSerializer):
    """
    Accepts a Facebook access_token from frontend, verifies it with Facebook,
    then links/creates a user + SocialAccount.
    """
    provider_name = "facebook"

    def validate(self, attrs):
        token = attrs["access_token"]

        resp = requests.get(
            "https://graph.facebook.com/me",
            params={
                "access_token": token,
                "fields": "id,email,first_name,last_name,picture",
            },
            timeout=5,
        )
        if resp.status_code != 200:
            raise ValidationError("Invalid Facebook access token.")

        data = resp.json()
        email = data.get("email")
        uid = data.get("id")

        if not email:
            raise ValidationError("Email not provided by Facebook.")

        picture = None
        if isinstance(data.get("picture"), dict):
            picture = data["picture"].get("data", {}).get("url")

        defaults = {
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "avatar_url": picture or "",
        }

        user, is_new = self.get_or_create_social_user(
            email=email,
            uid=uid,
            defaults=defaults,
        )

        if not user.is_active:
            raise AuthenticationFailed("Account deactivated. Please contact support.")

        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed("Account blocked. Please contact support.")

        attrs["user"] = user
        attrs["is_new"] = is_new
        return attrs
