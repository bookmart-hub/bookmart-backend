from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
)
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.authentication.models import User
from apps.marketplace.models import BookListing
from apps.marketplace.pagination import NearbyListingPagination
from apps.reviews.models import Review
from apps.reviews.serializers import (
    ReviewCreateSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
    SellerRatingSummarySerializer,
)
from apps.reviews.services import (
    create_review,
    delete_review,
    get_seller_reviews,
    seller_rating_summary,
    update_review,
)


class ReviewListCreateView(views.APIView):
    """
    POST /api/v1/reviews/ - Create a review (authenticated)
    GET /api/v1/reviews/ - List my reviews (authenticated, paginated)
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Create a review",
        description="Create a review for a listing. You cannot review your own listing or review the same listing twice.",
        request=ReviewCreateSerializer,
        responses={
            201: ReviewSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Create review",
                summary="Create a 5-star review",
                value={"listing": 1, "rating": 5, "review": "Excellent book, great condition!"},
                request_only=True,
            ),
        ],
        tags=["Reviews"],
    )
    def post(self, request, *args, **kwargs):
        serializer = ReviewCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        review = create_review(
            reviewer=request.user,
            listing=validated["listing"],
            rating=validated["rating"],
            review_text=validated.get("review", ""),
        )
        response_serializer = ReviewSerializer(review, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="List my reviews",
        description="Returns a paginated list of reviews written by the authenticated user.",
        responses={200: ReviewSerializer(many=True)},
        tags=["Reviews"],
    )
    def get(self, request, *args, **kwargs):
        qs = Review.objects.filter(reviewer=request.user).select_related(
            "seller", "listing", "listing__book"
        ).prefetch_related("listing__listing_images")
        paginator = NearbyListingPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = ReviewSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReviewDetailView(views.APIView):
    """
    PATCH /api/v1/reviews/{id}/ - Update review (owner only)
    DELETE /api/v1/reviews/{id}/ - Delete review (owner only)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            return Review.objects.select_related("reviewer", "seller", "listing").get(pk=pk)
        except Review.DoesNotExist:
            return None

    @extend_schema(
        summary="Update a review",
        description="Partially update your own review. Only the reviewer can update.",
        request=ReviewUpdateSerializer,
        responses={
            200: ReviewSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Update review",
                summary="Update rating and review text",
                value={"rating": 4, "review": "Updated review text."},
                request_only=True,
            ),
        ],
        tags=["Reviews"],
    )
    def patch(self, request, pk, *args, **kwargs):
        review = self.get_object(pk)
        if review is None:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            review = update_review(
                review=review,
                user=request.user,
                rating=serializer.validated_data.get("rating", review.rating),
                review_text=serializer.validated_data.get("review", review.review),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        response_serializer = ReviewSerializer(review, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete a review",
        description="Permanently delete your own review. Only the reviewer can delete.",
        responses={
            204: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Reviews"],
    )
    def delete(self, request, pk, *args, **kwargs):
        review = self.get_object(pk)
        if review is None:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            delete_review(review=review, user=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SellerReviewsView(views.APIView):
    """
    GET /api/v1/sellers/{id}/reviews/ - List reviews for a seller (paginated, newest first)
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="List seller reviews",
        description="Returns a paginated list of reviews for a specific seller, ordered by newest first.",
        responses={200: ReviewSerializer(many=True)},
        tags=["Reviews"],
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page number for paginated results.",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Number of results per page (max 100).",
            ),
        ],
    )
    def get(self, request, seller_id, *args, **kwargs):
        try:
            seller = User.objects.get(pk=seller_id)
        except User.DoesNotExist:
            return Response({"detail": "Seller not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = get_seller_reviews(seller)
        paginator = NearbyListingPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = ReviewSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerRatingSummaryView(views.APIView):
    """
    GET /api/v1/sellers/{id}/rating-summary/ - Get rating summary for a seller
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Get seller rating summary",
        description="Returns average rating, total count, and rating distribution for a seller.",
        responses={200: SellerRatingSummarySerializer},
        tags=["Reviews"],
        examples=[
            OpenApiExample(
                "Rating summary",
                summary="Seller rating summary",
                value={
                    "average_rating": 4.5,
                    "rating_count": 140,
                    "rating_distribution": {
                        "5": 120,
                        "4": 18,
                        "3": 2,
                        "2": 0,
                        "1": 0,
                    },
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, seller_id, *args, **kwargs):
        try:
            seller = User.objects.get(pk=seller_id)
        except User.DoesNotExist:
            return Response({"detail": "Seller not found."}, status=status.HTTP_404_NOT_FOUND)

        summary = seller_rating_summary(seller)
        serializer = SellerRatingSummarySerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)
