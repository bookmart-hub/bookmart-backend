from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.requirements.models import BookRequirement

User = get_user_model()


class RequirementUserSerializer(serializers.ModelSerializer):
    """Lightweight user representation for requirement responses."""

    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "profile_image"]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image(self, obj):
        if hasattr(obj, "profile") and obj.profile.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile.image.url)
            return obj.profile.image.url
        return None


class BookRequirementListSerializer(serializers.ModelSerializer):
    """Serializer for the public list view (anyone can see these)."""

    user = RequirementUserSerializer(read_only=True)

    class Meta:
        model = BookRequirement
        fields = [
            "id",
            "user",
            "book_title",
            "preferred_condition",
            "min_price",
            "max_price",
            "notes",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at", "updated_at"]


class BookRequirementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new requirement."""

    class Meta:
        model = BookRequirement
        fields = [
            "book_title",
            "preferred_condition",
            "min_price",
            "max_price",
            "notes",
        ]

    def validate_book_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Book title is required.")
        if len(value) > 255:
            raise serializers.ValidationError(
                "Book title must not exceed 255 characters."
            )
        return value

    def validate_min_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Minimum price cannot be negative.")
        return value

    def validate_max_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Maximum price cannot be negative.")
        return value

    def validate_preferred_condition(self, value):
        if value not in BookRequirement.Condition.values:
            raise serializers.ValidationError(
                f"Invalid condition. Must be one of: {', '.join(BookRequirement.Condition.values)}."
            )
        return value

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")

        if min_price is not None and max_price is not None:
            if max_price < min_price:
                raise serializers.ValidationError(
                    {"max_price": "Maximum price must be greater than or equal to minimum price."}
                )

        return attrs


class BookRequirementUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a requirement (owner only)."""

    class Meta:
        model = BookRequirement
        fields = [
            "book_title",
            "preferred_condition",
            "min_price",
            "max_price",
            "notes",
            "status",
        ]

    def validate_book_title(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Book title is required.")
            if len(value) > 255:
                raise serializers.ValidationError(
                    "Book title must not exceed 255 characters."
                )
        return value

    def validate_min_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Minimum price cannot be negative.")
        return value

    def validate_max_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Maximum price cannot be negative.")
        return value

    def validate_preferred_condition(self, value):
        if value is not None and value not in BookRequirement.Condition.values:
            raise serializers.ValidationError(
                f"Invalid condition. Must be one of: {', '.join(BookRequirement.Condition.values)}."
            )
        return value

    def validate_status(self, value):
        if value is not None and value not in BookRequirement.Status.values:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(BookRequirement.Status.values)}."
            )
        return value

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")

        if min_price is not None and max_price is not None:
            if max_price < min_price:
                raise serializers.ValidationError(
                    {"max_price": "Maximum price must be greater than or equal to minimum price."}
                )

        return attrs
