from django.contrib.auth import get_user_model
from django.db.models import Count
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.books.models import Author, Book
from apps.marketplace.models import BookListing, BookListingImage, Wishlist, PlatformNotification, BookContactLedger

User = get_user_model()


class AuthorNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name"]


class BookNestedSerializer(serializers.ModelSerializer):
    authors = AuthorNestedSerializer(many=True, read_only=True)
    genres = serializers.SerializerMethodField()

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
            "genres",
            "description",
            "publisher",
            "published_date",
            "language",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_genres(self, obj):
        return [g.name for g in obj.genres.all()]


class SellerNestedSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "profile_image", "phone_number"]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image(self, obj):
        if hasattr(obj, "profile") and obj.profile.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile.image.url)
            return obj.profile.image.url
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
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

    @extend_schema_field(serializers.URLField(allow_null=True))
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
    favorite_count = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

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
            "favorite_count",
            "is_favorited",
            "tags",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_favorite_count(self, obj):
        if hasattr(obj, "favorite_count"):
            return obj.favorite_count
        return Wishlist.objects.filter(listing=obj).count()

    @extend_schema_field(serializers.BooleanField)
    def get_is_favorited(self, obj):
        if hasattr(obj, "is_favorited"):
            return obj.is_favorited
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(user=request.user, listing=obj).exists()
        return False

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_tags(self, obj):
        return [t.tag.name for t in obj.tags.all()]


class NearbyBookListingSerializer(BookListingResponseSerializer):
    distance_km = serializers.FloatField(read_only=True)

    class Meta(BookListingResponseSerializer.Meta):
        fields = BookListingResponseSerializer.Meta.fields + ["distance_km"]


class BookListingCreateSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(required=False, write_only=True)
    openlibrary_key = serializers.CharField(required=False, write_only=True)
    title = serializers.CharField(required=False, write_only=True)
    author = serializers.CharField(required=False, write_only=True)
    genre = serializers.CharField(required=False, write_only=True, allow_blank=True)
    genres = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    category = serializers.CharField(required=False, write_only=True, allow_blank=True)
    categories = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)

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
            "genre",
            "genres",
            "category",
            "categories",
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

        if not book_id and not openlibrary_key and (not title or not author):
            raise serializers.ValidationError(
                "To manually create/associate a book listing, you must provide both 'title' and 'author'."
            )

        return attrs


class BookListingUpdateSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(required=False, write_only=True)
    openlibrary_key = serializers.CharField(required=False, write_only=True)
    title = serializers.CharField(required=False, write_only=True)
    author = serializers.CharField(required=False, write_only=True)
    genre = serializers.CharField(required=False, write_only=True, allow_blank=True)
    genres = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    category = serializers.CharField(required=False, write_only=True, allow_blank=True)
    categories = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)

    front_cover = serializers.ImageField(required=False, write_only=True, allow_null=True)
    back_cover = serializers.ImageField(required=False, write_only=True, allow_null=True)
    spine = serializers.ImageField(required=False, write_only=True, allow_null=True)
    middle_page = serializers.ImageField(required=False, write_only=True, allow_null=True)
    damage_1 = serializers.ImageField(required=False, write_only=True, allow_null=True)
    damage_2 = serializers.ImageField(required=False, write_only=True, allow_null=True)

    removed_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        default=list,
    )

    class Meta:
        model = BookListing
        fields = [
            "price",
            "condition",
            "condition_notes",
            "status",
            "latitude",
            "longitude",
            "book_id",
            "openlibrary_key",
            "title",
            "author",
            "genre",
            "genres",
            "category",
            "categories",
            "front_cover",
            "back_cover",
            "spine",
            "middle_page",
            "damage_1",
            "damage_2",
            "removed_image_ids",
        ]

    def validate(self, attrs):
        book_id = attrs.get("book_id")
        openlibrary_key = attrs.get("openlibrary_key")
        title = attrs.get("title")
        author = attrs.get("author")

        book_fields_provided = any([book_id, openlibrary_key, title, author])
        if book_fields_provided:
            has_explicit_book = any([book_id, openlibrary_key])
            has_manual_book = title and author
            has_partial_manual = (title and not author) or (author and not title)

            if not any([has_explicit_book, has_manual_book]):
                if has_partial_manual:
                    raise serializers.ValidationError(
                        "To update book details, you must provide both 'title' and 'author'."
                    )
                raise serializers.ValidationError(
                    "Invalid book identifier combination."
                )

        return attrs

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_removed_image_ids(self, value):
        listing = self.instance
        if listing and value:
            valid_ids = set(listing.listing_images.values_list("id", flat=True))
            invalid_ids = set(value) - valid_ids
            if invalid_ids:
                raise serializers.ValidationError(
                    f"Image IDs {sorted(invalid_ids)} do not belong to this listing."
                )
        return value

    def _validate_image_file(self, value):
        if value is not None and value:
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image size must not exceed 5 MB.")
            if not value.content_type.startswith("image/"):
                raise serializers.ValidationError("Only image files are allowed.")
        return value

    def validate_front_cover(self, value):
        return self._validate_image_file(value)

    def validate_back_cover(self, value):
        return self._validate_image_file(value)

    def validate_spine(self, value):
        return self._validate_image_file(value)

    def validate_middle_page(self, value):
        return self._validate_image_file(value)

    def validate_damage_1(self, value):
        return self._validate_image_file(value)

    def validate_damage_2(self, value):
        return self._validate_image_file(value)


class WishlistResponseSerializer(serializers.ModelSerializer):
    listing = BookListingResponseSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "listing", "created_at"]


class WishlistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ["listing"]

    def validate(self, attrs):
        user = self.context["request"].user
        listing = attrs.get("listing")
        if Wishlist.objects.filter(user=user, listing=listing).exists():
            raise serializers.ValidationError("This book listing is already in your wishlist.")
        return attrs


class PlatformNotificationSerializer(serializers.ModelSerializer):
    related_listing = BookListingResponseSerializer(read_only=True)
    action_trigger_user = SellerNestedSerializer(read_only=True)

    class Meta:
        model = PlatformNotification
        fields = [
            "id",
            "notification_type",
            "title",
            "body",
            "related_listing",
            "action_trigger_user",
            "is_read",
            "created_at",
        ]


class BookContactLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookContactLedger
        fields = [
            "id",
            "contact_person_name",
            "book_title",
            "deal_type",
            "price_recorded",
            "transaction_date",
        ]
