from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.books.models import Author, Book
from apps.marketplace.models import BookListing, BookListingImage

User = get_user_model()


class AuthorNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name"]


class BookNestedSerializer(serializers.ModelSerializer):
    authors = AuthorNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "authors",
            "cover_url",
            "isbn_13",
            "isbn_10",
            "openlibrary_key",
        ]


class SellerNestedSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "profile_image", "phone_number"]

    def get_profile_image(self, obj):
        if hasattr(obj, "profile") and obj.profile.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile.image.url)
            return obj.profile.image.url
        return None

    def get_phone_number(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.phone_number
        return None


class BookListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BookListingImage
        fields = ["id", "book_listing", "image", "image_url", "label", "created_at"]
        extra_kwargs = {"image": {"write_only": True}}

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class BookListingResponseSerializer(serializers.ModelSerializer):
    book = BookNestedSerializer(read_only=True)
    seller = SellerNestedSerializer(read_only=True)
    listing_images = BookListingImageSerializer(many=True, read_only=True)

    class Meta:
        model = BookListing
        fields = [
            "id",
            "book",
            "seller",
            "price",
            "condition",
            "condition_notes",
            "status",
            "listing_images",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]


class BookListingCreateSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(required=False, write_only=True)
    openlibrary_key = serializers.CharField(required=False, write_only=True)
    title = serializers.CharField(required=False, write_only=True)
    author = serializers.CharField(required=False, write_only=True)

    front_cover = serializers.ImageField(required=True, write_only=True)
    back_cover = serializers.ImageField(required=True, write_only=True)
    spine = serializers.ImageField(required=True, write_only=True)
    middle_page = serializers.ImageField(required=True, write_only=True)
    damage_1 = serializers.ImageField(required=False, write_only=True, allow_null=True)
    damage_2 = serializers.ImageField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = BookListing
        fields = [
            "price",
            "condition",
            "condition_notes",
            "latitude",
            "longitude",
            "book_id",
            "openlibrary_key",
            "title",
            "author",
            "front_cover",
            "back_cover",
            "spine",
            "middle_page",
            "damage_1",
            "damage_2",
        ]

    def validate(self, attrs):
        book_id = attrs.get("book_id")
        openlibrary_key = attrs.get("openlibrary_key")
        title = attrs.get("title")
        author = attrs.get("author")

        if not any([book_id, openlibrary_key, (title and author)]):
            raise serializers.ValidationError(
                "You must provide either a 'book_id', an 'openlibrary_key', or both 'title' and 'author' for manual entry."
            )

        if (title and not author) or (author and not title):
            raise serializers.ValidationError(
                "To manually create/associate a book listing, you must provide both 'title' and 'author'."
            )

        return attrs
