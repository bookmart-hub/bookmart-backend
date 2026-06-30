from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.authentication.models import College, Profile

User = get_user_model()


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ["id", "name", "district", "state"]


class UserProfileSerializer(serializers.ModelSerializer):
    college = CollegeSerializer(read_only=True)
    college_id = serializers.PrimaryKeyRelatedField(
        queryset=College.objects.all(),
        write_only=True,
        source="college",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Profile
        fields = [
            "full_name",
            "phone_number",
            "college",
            "college_id",
            "department_stream",
            "city_location",
            "is_top_seller",
            "latitude",
            "longitude",
        ]
        read_only_fields = ["is_top_seller"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "full_name"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value.lower()

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        password = validated_data.pop("password")

        # Create user instance cleanly via our Custom User Manager
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        # Profile is automatically instantiated, update its full name
        profile = user.profile
        profile.full_name = full_name
        profile.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "email_verified", "profile"]
