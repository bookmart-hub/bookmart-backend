from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.authentication.models import User
from apps.core.serializers import ProfileResponseSerializer


class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(write_only=True)


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password", "full_name"]
        read_only_fields = [
            "id",
            "email_verified",
            "provider",
            "created_at",
        ]

    def validate_email(self, value):
        value = get_user_model().objects.normalize_email(value)

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "full_name",
        ]
        read_only_fields = [
            "id",
            "email_verified",
            "provider",
            "created_at",
        ]


class UserResponseSerializer(serializers.ModelSerializer):
    profile = ProfileResponseSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "provider",
            "email_verified",
            "created_at",
            "profile",
        ]
        read_only_fields = [
            "id",
            "email_verified",
            "provider",
            "created_at",
        ]


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        User = get_user_model()
        normalized_email = User.objects.normalize_email(value)
        if not User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("No account found with this email address.")
        return normalized_email


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=User.AuthProvider.choices)
    provider_id = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        provider = attrs["provider"]
        provider_id = attrs["provider_id"]
        email = attrs["email"].lower()
        full_name = attrs.get("full_name") or email.split("@")[0]

        # Get or create user
        try:
            user = User.objects.get(email__iexact=email)
            if user.provider == User.AuthProvider.EMAIL:
                # Link native account with social account
                user.provider = provider
                user.provider_id = provider_id
                user.email_verified = True
                user.save()
            elif user.provider != provider:
                raise serializers.ValidationError(
                    f"This email is registered with {user.provider} sign-in."
                )
        except User.DoesNotExist:
            user = User.objects.create(
                email=email,
                full_name=full_name,
                provider=provider,
                provider_id=provider_id,
                email_verified=True,
            )
            user.set_unusable_password()
            user.save()

        attrs["user"] = user
        return attrs

