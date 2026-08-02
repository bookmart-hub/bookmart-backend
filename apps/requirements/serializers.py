from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.books.models import Book
from apps.requirements.models import BookRequirement
from apps.requirements.services import find_matching_requirements

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


class BookNestedSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["id", "title", "cover_url", "author"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author(self, obj):
        first_author = obj.authors.first()
        return first_author.name if first_author else None


class BookRequirementListSerializer(serializers.ModelSerializer):
    """Serializer for the public list view (anyone can see these)."""

    user = RequirementUserSerializer(read_only=True)
    book = BookNestedSerializer(read_only=True)
    matching_count = serializers.SerializerMethodField()

    class Meta:
        model = BookRequirement
        fields = [
            "id",
            "user",
            "book",
            "book_title",
            "preferred_condition",
            "min_price",
            "max_price",
            "notes",
            "status",
            "matching_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "book",
            "status",
            "matching_count",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_matching_count(self, obj):
        return find_matching_requirements(obj).count()


class BookRequirementNearbySerializer(BookRequirementListSerializer):
    """Extends list serializer with computed distance for nearby endpoint."""

    distance_km = serializers.FloatField(read_only=True)

    class Meta(BookRequirementListSerializer.Meta):
        fields = BookRequirementListSerializer.Meta.fields + ["distance_km"]


class BookRequirementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new requirement."""

    book_id = serializers.IntegerField(required=False, write_only=True)
    book_title = serializers.CharField(required=False)
    latitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)

    class Meta:
        model = BookRequirement
        fields = [
            "book_id",
            "book_title",
            "preferred_condition",
            "min_price",
            "max_price",
            "notes",
            "latitude",
            "longitude",
        ]

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
        book_id = attrs.get("book_id")
        book_title = attrs.get("book_title")

        if not book_id and not book_title:
            raise serializers.ValidationError(
                "You must provide either 'book_id' or 'book_title'."
            )

        book = None
        if book_id:
            try:
                book = Book.objects.get(id=book_id)
            except Book.DoesNotExist:
                raise serializers.ValidationError(
                    {"book_id": "No book found with the provided book_id."}
                )
            if not book_title:
                attrs["book_title"] = book.title

        attrs["book"] = book

        if "book_title" in attrs:
            attrs["book_title"] = attrs["book_title"].strip()
            if not attrs["book_title"]:
                raise serializers.ValidationError(
                    {"book_title": "Book title is required."}
                )
            if len(attrs["book_title"]) > 255:
                raise serializers.ValidationError(
                    {"book_title": "Book title must not exceed 255 characters."}
                )

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

    book_id = serializers.IntegerField(required=False, write_only=True)
    latitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)

    class Meta:
        model = BookRequirement
        fields = [
            "book_id",
            "book_title",
            "preferred_condition",
            "min_price",
            "max_price",
            "notes",
            "status",
            "latitude",
            "longitude",
        ]

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
        book_id = attrs.get("book_id")
        book_title = attrs.get("book_title")

        book = None
        if book_id:
            try:
                book = Book.objects.get(id=book_id)
            except Book.DoesNotExist:
                raise serializers.ValidationError(
                    {"book_id": "No book found with the provided book_id."}
                )
            if not book_title:
                attrs["book_title"] = book.title

        attrs["book"] = book

        if "book_title" in attrs:
            attrs["book_title"] = attrs["book_title"].strip()
            if not attrs["book_title"]:
                raise serializers.ValidationError(
                    {"book_title": "Book title is required."}
                )
            if len(attrs["book_title"]) > 255:
                raise serializers.ValidationError(
                    {"book_title": "Book title must not exceed 255 characters."}
                )

        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")
        if min_price is not None and max_price is not None:
            if max_price < min_price:
                raise serializers.ValidationError(
                    {"max_price": "Maximum price must be greater than or equal to minimum price."}
                )

        return attrs
