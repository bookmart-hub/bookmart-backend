from rest_framework import serializers


class BookSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    openlibrary_key = serializers.CharField(required=False, allow_null=True)
    title = serializers.CharField()
    authors = serializers.ListField(child=serializers.CharField())
    isbn13 = serializers.CharField(allow_null=True, required=False)
    published_year = serializers.IntegerField(allow_null=True, required=False)
    cover_url = serializers.URLField(allow_null=True, required=False, allow_blank=True)
    categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)
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
    categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)
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
            raise serializers.ValidationError("At least one author must be specified in 'author' or 'authors'.")
        return attrs

