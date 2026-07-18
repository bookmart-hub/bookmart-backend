from rest_framework import serializers


class BookSearchSerializer(serializers.Serializer):
    openlibrary_key = serializers.CharField()
    title = serializers.CharField()
    authors = serializers.ListField(child=serializers.CharField())
    isbn13 = serializers.CharField(allow_null=True)
    published_year = serializers.IntegerField(allow_null=True)
    cover_url = serializers.URLField(allow_null=True)


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
