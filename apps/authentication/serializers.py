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
