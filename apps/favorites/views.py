from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
)
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.favorites.serializers import (
    FavoriteCheckSerializer,
    FavoriteCountSerializer,
    FavoriteCreateSerializer,
    FavoriteListingSerializer,
)
from apps.favorites.services import (
    add_favorite,
    favorite_count,
    is_favorited,
    list_favorites,
    remove_favorite,
)
from apps.marketplace.pagination import NearbyListingPagination


class FavoriteListCreateView(views.APIView):
    """
    GET  /api/v1/favorites/          — List my favorite listings (paginated, newest first)
    POST /api/v1/favorites/          — Add a listing to favorites
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List my favorite listings",
        description="Returns a paginated list of the authenticated user's favorite listings, ordered by newest saved first.",
        responses={200: FavoriteListingSerializer(many=True)},
        tags=["Favorites"],
    )
    def get(self, request, *args, **kwargs):
        qs = list_favorites(user=request.user)

        paginator = NearbyListingPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = FavoriteListingSerializer(
                page, many=True, context={"request": request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = FavoriteListingSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Add a listing to favorites",
        description="Save a listing to the authenticated user's favorites.",
        request=FavoriteCreateSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Add favorite",
                summary="Save a listing to favorites",
                value={"listing": 15},
                request_only=True,
            ),
            OpenApiExample(
                "Favorite created",
                summary="Listing saved successfully",
                value={"detail": "Listing saved successfully."},
                response_only=True,
            ),
            OpenApiExample(
                "Duplicate favorite",
                summary="Already in favorites",
                value={"detail": "Listing is already in your favorites."},
                response_only=True,
            ),
            OpenApiExample(
                "Own listing",
                summary="Cannot favorite own listing",
                value={"detail": "Cannot favorite your own listing."},
                response_only=True,
            ),
        ],
        tags=["Favorites"],
    )
    def post(self, request, *args, **kwargs):
        serializer = FavoriteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing_id = serializer.validated_data["listing"]

        try:
            add_favorite(user=request.user, listing_id=listing_id)
        except ValueError as e:
            detail = str(e)
            if "already in your favorites" in detail:
                return Response(
                    {"detail": detail},
                    status=status.HTTP_409_CONFLICT,
                )
            if "Cannot favorite" in detail:
                return Response(
                    {"detail": detail},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if "not found" in detail.lower():
                return Response(
                    {"detail": detail},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Listing saved successfully."},
            status=status.HTTP_201_CREATED,
        )


class FavoriteDeleteView(views.APIView):
    """
    DELETE /api/v1/favorites/{listing_id}/  — Remove a listing from favorites
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Remove a listing from favorites",
        description="Remove a saved listing from the authenticated user's favorites.",
        responses={
            204: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Favorites"],
    )
    def delete(self, request, listing_id, *args, **kwargs):
        try:
            remove_favorite(user=request.user, listing_id=listing_id)
        except ValueError as e:
            detail = str(e)
            if "not in favorites" in detail:
                return Response(
                    {"detail": detail},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteCheckView(views.APIView):
    """
    GET /api/v1/favorites/check/{listing_id}/  — Check if listing is saved
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Check if listing is favorited",
        description="Returns whether the authenticated user has saved the given listing.",
        responses={200: FavoriteCheckSerializer},
        tags=["Favorites"],
    )
    def get(self, request, listing_id, *args, **kwargs):
        saved = is_favorited(user=request.user, listing_id=listing_id)
        serializer = FavoriteCheckSerializer({"saved": saved})
        return Response(serializer.data, status=status.HTTP_200_OK)


class FavoriteCountView(views.APIView):
    """
    GET /api/v1/favorites/count/{listing_id}/  — Get total favorite count for a listing
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Get favorite count for a listing",
        description="Returns the total number of users who have favorited the given listing. Public endpoint.",
        responses={200: FavoriteCountSerializer},
        tags=["Favorites"],
    )
    def get(self, request, listing_id, *args, **kwargs):
        count = favorite_count(listing_id=listing_id)
        serializer = FavoriteCountSerializer({"count": count})
        return Response(serializer.data, status=status.HTTP_200_OK)


class FavoriteAdminView(views.APIView):
    """
    GET /api/v1/favorites/admin/  — Admin: view all favorites
    """

    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        summary="Admin: list all favorites",
        description="Admin-only endpoint to view all favorites. Supports search and filtering.",
        responses={200: FavoriteListingSerializer(many=True)},
        tags=["Favorites"],
    )
    def get(self, request, *args, **kwargs):
        from django.db.models import Q
        from apps.marketplace.models import BookListing, Wishlist

        qs = Wishlist.objects.select_related(
            "user", "listing", "listing__book", "listing__seller"
        ).all()

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(listing__book__title__icontains=search)
                | Q(listing__seller__email__icontains=search)
                | Q(listing__seller__full_name__icontains=search)
            )

        qs = qs.order_by("-created_at")

        paginator = NearbyListingPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            data = []
            for wishlist_item in page:
                data.append({
                    "id": wishlist_item.listing.id,
                    "book": {
                        "id": wishlist_item.listing.book.id,
                        "title": wishlist_item.listing.book.title,
                        "authors": [],
                        "cover_url": wishlist_item.listing.book.cover_url,
                        "isbn_13": wishlist_item.listing.book.isbn_13,
                        "isbn_10": wishlist_item.listing.book.isbn_10,
                        "openlibrary_key": wishlist_item.listing.book.openlibrary_key,
                    },
                    "seller": {
                        "id": wishlist_item.listing.seller.id,
                        "full_name": wishlist_item.listing.seller.full_name,
                        "email": wishlist_item.listing.seller.email,
                        "profile_image": None,
                        "phone_number": None,
                    },
                    "price": str(wishlist_item.listing.price),
                    "condition": wishlist_item.listing.condition,
                    "condition_notes": wishlist_item.listing.condition_notes,
                    "status": wishlist_item.listing.status,
                    "listing_images": [],
                    "latitude": wishlist_item.listing.latitude,
                    "longitude": wishlist_item.listing.longitude,
                    "favorite_count": wishlist_item.listing.wishlisted_by.count(),
                    "is_favorited": True,
                    "created_at": wishlist_item.listing.created_at,
                    "updated_at": wishlist_item.listing.updated_at,
                })
            return paginator.get_paginated_response(data)

        data = []
        for wishlist_item in qs:
            data.append({
                "id": wishlist_item.listing.id,
                "book": {
                    "id": wishlist_item.listing.book.id,
                    "title": wishlist_item.listing.book.title,
                    "authors": [],
                    "cover_url": wishlist_item.listing.book.cover_url,
                    "isbn_13": wishlist_item.listing.book.isbn_13,
                    "isbn_10": wishlist_item.listing.book.isbn_10,
                    "openlibrary_key": wishlist_item.listing.book.openlibrary_key,
                },
                "seller": {
                    "id": wishlist_item.listing.seller.id,
                    "full_name": wishlist_item.listing.seller.full_name,
                    "email": wishlist_item.listing.seller.email,
                    "profile_image": None,
                    "phone_number": None,
                },
                "price": str(wishlist_item.listing.price),
                "condition": wishlist_item.listing.condition,
                "condition_notes": wishlist_item.listing.condition_notes,
                "status": wishlist_item.listing.status,
                "listing_images": [],
                "latitude": wishlist_item.listing.latitude,
                "longitude": wishlist_item.listing.longitude,
                "favorite_count": wishlist_item.listing.wishlisted_by.count(),
                "is_favorited": True,
                "created_at": wishlist_item.listing.created_at,
                "updated_at": wishlist_item.listing.updated_at,
            })
        return Response(data, status=status.HTTP_200_OK)
