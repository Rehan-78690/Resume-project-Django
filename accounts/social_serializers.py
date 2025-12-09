# accounts/social_serializers.py

import logging
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from allauth.socialaccount.models import SocialAccount

logger = logging.getLogger(__name__)

User = get_user_model()


class BaseSocialSerializer(serializers.Serializer):
    """
    Base serializer for social auth.

    - For Google we primarily use `id_token` (from @react-oauth/google),
      but we keep `access_token` optional so it doesn't break subclasses.
    - For Facebook we still require `access_token` in its own serializer.
    """
    access_token = serializers.CharField(required=False, allow_blank=True)

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
    Accepts a Google ID token (from @react-oauth/google),
    verifies it via Google's tokeninfo endpoint, then links/creates a user
    + SocialAccount.
    """
    provider_name = "google"

    # Frontend will send: { "id_token": "<JWT>" }  (we also accept access_token as fallback)
    id_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        raw_token = attrs.get("id_token") or attrs.get("access_token")
        if not raw_token:
            raise ValidationError("Google id_token is required.")

        # 1) Ask Google to validate the ID token
        try:
            resp = requests.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": raw_token},
                timeout=5,
            )
        except requests.RequestException as e:
            logger.error("Error calling Google tokeninfo: %s", e)
            raise ValidationError("Could not contact Google token endpoint.")

        if resp.status_code != 200:
            logger.warning(
                "Google tokeninfo returned non-200: %s, body=%s",
                resp.status_code,
                resp.text,
            )
            raise ValidationError("Invalid Google token.")

        data = resp.json()
        logger.debug("Google tokeninfo data: %s", data)

        # 2) Audience (client_id) must match our app’s client id
        aud = data.get("aud")
        expected_aud = getattr(settings, "GOOGLE_CLIENT_ID", None)
        if expected_aud and aud != expected_aud:
            logger.warning(
                "Google token audience mismatch: aud=%s expected=%s",
                aud,
                expected_aud,
            )
            raise ValidationError("Invalid Google token audience.")

        # 3) Issuer sanity-check
        iss = data.get("iss")
        if iss not in ["accounts.google.com", "https://accounts.google.com"]:
            logger.warning("Google token issuer invalid: %s", iss)
            raise ValidationError("Invalid Google token issuer.")

        # 4) Extract user info
        email = data.get("email")
        # tokeninfo returns 'true'/'false' strings
        email_verified = str(data.get("email_verified", "true")).lower() == "true"
        sub = data.get("sub")  # unique Google user id

        if not email:
            raise ValidationError("Google did not return an email.")
        if not email_verified:
            raise ValidationError("Google email not verified.")
        if not sub:
            raise ValidationError("Google did not return a user id.")

        defaults = {
            "first_name": data.get("given_name", "") or "",
            "last_name": data.get("family_name", "") or "",
            "avatar_url": data.get("picture", "") or "",
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

    # For Facebook we still REQUIRE access_token
    access_token = serializers.CharField(required=True)

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
            logger.warning(
                "Facebook token validation failed: %s, body=%s",
                resp.status_code,
                resp.text,
            )
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
            "first_name": data.get("first_name", "") or "",
            "last_name": data.get("last_name", "") or "",
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
