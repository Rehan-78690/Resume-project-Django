# accounts/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role", "is_blocked"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "role"]
        extra_kwargs = {
            "role": {"read_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.role = User.Roles.USER
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom login:
    - If email exists but password is wrong -> 'Incorrect password'
    - If email does not exist -> 'Invalid email or password'
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
            # Email doesn't exist -> generic error
            raise AuthenticationFailed("Invalid email or password")

        if not user.check_password(password):
            # Email is correct but password is wrong
            raise AuthenticationFailed("Incorrect password")

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

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
