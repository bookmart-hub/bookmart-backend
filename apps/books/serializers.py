from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.books.models import Category


class CategoryListSerializer(serializers.ModelSerializer):
    total_books_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "subtitle",
            "icon",
            "total_books_count",
            "created_at",
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_total_books_count(self, obj):
        if hasattr(obj, "total_books_count"):
            return obj.total_books_count
        return obj.books.count()


class ListedSellerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    profile_image = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image(self, obj):
        if hasattr(obj, "profile") and obj.profile.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile.image.url)
            return obj.profile.image.url
        return None


class BookListingRankedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    condition = serializers.CharField()
    condition_notes = serializers.CharField(allow_blank=True)
    seller = ListedSellerSerializer()
    cover_image_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_cover_image_url(self, obj):
        front_image = obj.listing_images.filter(label="FRONT_COVER").first()
        if not front_image:
            front_image = obj.listing_images.first()
        if front_image and front_image.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(front_image.image.url)
            return front_image.image.url
        return None


class CanonicalBookCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    cover_url = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()
    isbn_13 = serializers.CharField(allow_null=True)
    lowest_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    total_listings_count = serializers.SerializerMethodField()
    cheapest_listing = serializers.SerializerMethodField()
    listings = serializers.SerializerMethodField()

    def _get_ranked_listings(self, obj):
        if hasattr(obj, "ranked_listings"):
            return obj.ranked_listings
        return list(obj.listings.filter(status="AVAILABLE").order_by("price"))

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_cover_url(self, obj):
        if obj.cover_url:
            return obj.cover_url
        listings = self._get_ranked_listings(obj)
        if listings:
            first_img = listings[0].listing_images.first()
            if first_img and first_img.image:
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(first_img.image.url)
                return first_img.image.url
        return None

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_authors(self, obj):
        return [author.name for author in obj.authors.all()]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_lowest_price(self, obj):
        listings = self._get_ranked_listings(obj)
        if listings:
            return str(listings[0].price)
        return None

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_discount_percentage(self, obj):
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_total_listings_count(self, obj):
        return len(self._get_ranked_listings(obj))

    @extend_schema_field(BookListingRankedSerializer(allow_null=True))
    def get_cheapest_listing(self, obj):
        listings = self._get_ranked_listings(obj)
        if listings:
            return BookListingRankedSerializer(listings[0], context=self.context).data
        return None

    @extend_schema_field(BookListingRankedSerializer(many=True))
    def get_listings(self, obj):
        listings = self._get_ranked_listings(obj)
        return BookListingRankedSerializer(
            listings, many=True, context=self.context
        ).data


class CategoryDetailSerializer(serializers.ModelSerializer):
    total_books_count = serializers.SerializerMethodField()
    books = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "subtitle",
            "icon",
            "total_books_count",
            "created_at",
            "books",
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_total_books_count(self, obj):
        if hasattr(obj, "category_books"):
            return len(obj.category_books)
        return obj.books.count()

    @extend_schema_field(CanonicalBookCategorySerializer(many=True))
    def get_books(self, obj):
        if hasattr(obj, "category_books"):
            books_list = obj.category_books
        else:
            books_list = list(obj.books.all())
        return CanonicalBookCategorySerializer(
            books_list, many=True, context=self.context
        ).data


class BookCreatedResponseSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    book_id = serializers.IntegerField()
    title = serializers.CharField()
    cover_url = serializers.CharField(allow_blank=True, allow_null=True)
    published_year = serializers.IntegerField(allow_null=True)
    authors = serializers.ListField(child=serializers.CharField())
    categories = serializers.ListField(child=serializers.CharField())
    is_local = serializers.BooleanField(default=True)


class BookSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    openlibrary_key = serializers.CharField(required=False, allow_null=True)
    title = serializers.CharField()
    authors = serializers.ListField(child=serializers.CharField())
    isbn13 = serializers.CharField(allow_null=True, required=False)
    published_year = serializers.IntegerField(allow_null=True, required=False)
    cover_url = serializers.URLField(allow_null=True, required=False, allow_blank=True)
    categories = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    is_local = serializers.BooleanField(default=False)


class BookSerializer(serializers.Serializer):
    title = serializers.CharField()
    author_name = serializers.ListField()
    isbn = serializers.ListField(required=False)
    cover_id = serializers.IntegerField(required=False)
    publish_year = serializers.IntegerField(required=False)
    key = serializers.CharField()


class OpenLibraryImportSerializer(serializers.Serializer):
    title = serializers.CharField()
    author_name = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    isbn = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    cover_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )
    publish_year = serializers.IntegerField(
        required=False,
        allow_null=True,
    )
    key = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class BookImportSerializer(serializers.Serializer):
    openlibrary_key = serializers.CharField(max_length=100)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class BookManualCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    author = serializers.CharField(required=False, allow_blank=True)
    authors = serializers.ListField(child=serializers.CharField(), required=False)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    categories = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    description = serializers.CharField(required=False, allow_blank=True)
    publisher = serializers.CharField(required=False, allow_blank=True)
    published_year = serializers.IntegerField(required=False, allow_null=True)
    isbn_13 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    isbn_10 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cover_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        author = attrs.get("author")
        authors = attrs.get("authors")
        if not author and not authors:
            raise serializers.ValidationError(
                "At least one author must be specified in 'author' or 'authors'."
            )
        return attrs
