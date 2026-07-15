from rest_framework import serializers

from apps.core.models import College, Profile


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ["id", "name", "district", "state"]


class ProfileResponseSerializer(serializers.ModelSerializer):
    college = CollegeSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "image",
            "phone_number",
            "college",
            "city_location",
            "latitude",
            "longitude",
            "personalization_fields",
        ]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "phone_number",
            "date_of_birth",
            "bio",
            "college",
            "city_location",
            "latitude",
            "longitude",
            "personalization_fields",
        ]

    def validate_latitude(self, value):
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class ProfileImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["image"]

    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:  # 5 MB
            raise serializers.ValidationError("Image size must not exceed 5 MB.")

        if not value.content_type.startswith("image/"):
            raise serializers.ValidationError("Only image files are allowed.")

        return value


class ProfileOnboardingSerializer(serializers.ModelSerializer):
    USER_ROLE_CHOICES = (
        ("STUDENT", "Student"),
        ("TEACHER", "Teacher"),
        ("PROFESSIONAL", "Professional"),
        ("BOOK_LOVER", "Book Lover"),
        ("OTHERS", "Others"),
    )

    BOOK_PREFERENCE_CHOICES = (
        ("ACADEMIC", "Academic or Textbooks"),
        ("COMPETETIVE", "Competitive Exams"),
        ("FICTION", "Fiction"),
        ("SELF_HELP", "Self Help"),
        ("BUSINESS", "Business & Finance"),
        ("COMIC", "Comics & Manga"),
        ("NON_FICTION", "Non-Fiction"),
        ("TECHNOLOGY", "Technology"),
        ("OTHER", "Others"),
    )

    user_role = serializers.ChoiceField(choices=USER_ROLE_CHOICES)
    book_preferences = serializers.ChoiceField(choices=BOOK_PREFERENCE_CHOICES)

    college = CollegeSerializer(read_only=True)
    college_id = serializers.PrimaryKeyRelatedField(
        queryset=College.objects.all(),
        source="college",
        write_only=True,
    )

    class Meta:
        model = Profile
        fields = [
            "user_role",
            "college",
            "college_id",
            "book_preferences",
        ]

    def update(self, instance, validated_data):
        # Remove non-model fields
        user_role = validated_data.pop("user_role", None)
        book_preferences = validated_data.pop("book_preferences", None)

        # Update model fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update JSONField
        personalization = instance.personalization_fields or {}

        if user_role is not None:
            personalization["user_role"] = user_role

        if book_preferences is not None:
            personalization["book_preferences"] = book_preferences

        instance.personalization_fields = personalization
        instance.save()

        return instance
