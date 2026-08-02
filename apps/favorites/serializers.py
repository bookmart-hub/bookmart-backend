from rest_framework import serializers

from apps.marketplace.serializers import BookListingResponseSerializer


class FavoriteListingSerializer(BookListingResponseSerializer):
    """Reuses the existing BookListingResponseSerializer."""

    pass


class FavoriteCreateSerializer(serializers.Serializer):
    listing = serializers.IntegerField()


class FavoriteCheckSerializer(serializers.Serializer):
    saved = serializers.BooleanField()


class FavoriteCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
