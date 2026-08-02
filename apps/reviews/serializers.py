from rest_framework import serializers

from apps.reviews.models import Review
from apps.authentication.models import User


class ReviewerSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "profile_image"]

    def get_profile_image(self, obj):
        if hasattr(obj, "profile") and obj.profile.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile.image.url)
            return obj.profile.image.url
        return None


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = ReviewerSerializer(read_only=True)
    seller = ReviewerSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "reviewer",
            "seller",
            "listing",
            "rating",
            "review",
            "created_at",
            "updated_at",
        ]


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["listing", "rating", "review"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        reviewer = request.user
        listing = attrs.get("listing")

        if listing.seller == reviewer:
            raise serializers.ValidationError("You cannot review your own listing.")

        if Review.objects.filter(reviewer=reviewer, listing=listing).exists():
            raise serializers.ValidationError("You have already reviewed this listing.")

        attrs["reviewer"] = reviewer
        attrs["seller"] = listing.seller
        return attrs

    def create(self, validated_data):
        return Review.objects.create(**validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "review"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class SellerRatingSummarySerializer(serializers.Serializer):
    average_rating = serializers.FloatField()
    rating_count = serializers.IntegerField()
    rating_distribution = serializers.DictField()
