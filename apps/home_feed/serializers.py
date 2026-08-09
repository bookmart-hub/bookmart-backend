from rest_framework import serializers

from apps.marketplace.serializers import BookListingResponseSerializer
from apps.books.serializers import GenreListSerializer


class HomeFeedSerializer(serializers.Serializer):
    profile_completion = serializers.IntegerField()
    nearby_books = BookListingResponseSerializer(many=True)
    latest_books = BookListingResponseSerializer(many=True)
    popular_books = BookListingResponseSerializer(many=True)
    recommended_books = BookListingResponseSerializer(many=True)
    featured_books = BookListingResponseSerializer(many=True)
    genres = GenreListSerializer(many=True)
    stats = serializers.DictField()
