from django.db.models import Count, Exists, OuterRef, Value, BooleanField
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.marketplace.models import BookListing, Wishlist, PlatformNotification, BookContactLedger
from apps.marketplace.pagination import NearbyListingPagination
from apps.marketplace.serializers import (
    BookListingCreateSerializer,
    BookListingResponseSerializer,
    BookListingUpdateSerializer,
    NearbyBookListingSerializer,
    WishlistResponseSerializer,
    WishlistCreateSerializer,
    PlatformNotificationSerializer,
    BookContactLedgerSerializer,
)
from apps.marketplace.services import (
    DEFAULT_RADIUS_KM,
    MAX_RADIUS_KM,
    create_book_listing,
    get_nearby_listings,
    update_book_listing,
)


import django_filters

class BookListingFilter(django_filters.FilterSet):
    genre = django_filters.CharFilter(field_name="book__genres__slug")
    tag = django_filters.CharFilter(field_name="book__tags__tag__slug")

    class Meta:
        model = BookListing
        fields = ["condition", "status", "book", "genre", "tag"]

@extend_schema_view(
    list=extend_schema(
        summary="List book listings",
        description="Retrieve a list of all active/available book listings. Supports searching by book title or author, and filtering by condition or status.",
        tags=["Book Listings"],
    ),
    retrieve=extend_schema(
        summary="Retrieve book listing details",
        description="Fetches full details of a specific book listing.",
        tags=["Book Listings"],
    ),
    create=extend_schema(
        summary="Create a new book listing",
        description="Creates a new listing for a book. Can link to an existing catalog book, import from OpenLibrary by key, or create a custom book with title and author. Requires uploading Front Cover, Back Cover, Spine, and Middle Page photos.",
        request=BookListingCreateSerializer,
        responses={201: BookListingResponseSerializer},
        tags=["Book Listings"],
    ),
    update=extend_schema(
        summary="Update a book listing",
        description="Full update of an existing book listing. Only the owner can update their listing.",
        request=BookListingUpdateSerializer,
        responses={200: BookListingResponseSerializer},
        tags=["Book Listings"],
    ),
    partial_update=extend_schema(
        summary="Partially update a book listing",
        description="Partial update of an existing book listing. Only the owner can update their listing. For multipart form data, empty optional fields and placeholder values are ignored.",
        request=BookListingUpdateSerializer,
        responses={200: BookListingResponseSerializer},
        tags=["Book Listings"],
    ),
    destroy=extend_schema(
        summary="Delete a book listing",
        description="Deletes an existing book listing.",
        tags=["Book Listings"],
    ),
)
class BookListingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    search_fields = ["book__title", "book__authors__name"]
    filterset_class = BookListingFilter
    ordering_fields = ["price", "created_at"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_queryset(self):
        qs = BookListing.objects.select_related(
            "book", "seller", "seller__profile"
        ).prefetch_related("book__authors", "listing_images")

        qs = qs.annotate(
            favorite_count=Count("wishlisted_by"),
        )

        if self.request.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=self.request.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        return qs.all()

    def get_serializer_class(self):
        if self.action == "create":
            return BookListingCreateSerializer
        if self.action in ["update", "partial_update"]:
            return BookListingUpdateSerializer
        return BookListingResponseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            listing = create_book_listing(
                seller=request.user,
                data=serializer.validated_data,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = BookListingResponseSerializer(
            listing, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    def _normalize_patch_data(self, data):
        """Sanitize multipart form PATCH data so empty/placeholder optional fields are ignored."""
        # Convert immutable QueryDict to mutable dict
        if hasattr(data, "lists"):
            cleaned = {}
            for key, values in data.lists():
                cleaned[key] = values[0] if len(values) == 1 else values
        else:
            cleaned = dict(data)

        # Remove fields with empty string values
        cleaned = {key: value for key, value in cleaned.items() if value != ""}

        # removed_image_ids: ignore if empty, '0', or list of only invalid values
        if "removed_image_ids" in cleaned:
            raw = cleaned["removed_image_ids"]
            ids = []
            if isinstance(raw, list):
                ids = [
                    int(v.strip())
                    for v in raw
                    if str(v).strip() not in ("", "0") and str(v).strip().isdigit()
                ]
            else:
                val = str(raw).strip()
                if val not in ("", "0") and val.isdigit():
                    ids = [int(val)]

            if ids:
                cleaned["removed_image_ids"] = ids
            else:
                del cleaned["removed_image_ids"]

        # categories: ignore if empty
        if "categories" in cleaned:
            raw = cleaned["categories"]
            if raw == "" or (isinstance(raw, list) and len(raw) == 1 and raw[0] == ""):
                del cleaned["categories"]

        # Remove empty uploaded files
        for key in list(cleaned.keys()):
            value = cleaned[key]
            if hasattr(value, "size") and value.size == 0:
                del cleaned[key]

        return cleaned

    def _update_listing(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.seller != request.user:
            return Response(
                {"detail": "You do not have permission to edit this listing."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        if self.action == "partial_update":
            data = self._normalize_patch_data(data)

        serializer = self.get_serializer(
            instance, data=data, partial=self.action == "partial_update"
        )
        serializer.is_valid(raise_exception=True)

        try:
            listing = update_book_listing(
                listing=instance,
                user=request.user,
                data=serializer.validated_data,
            )
        except PermissionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = BookListingResponseSerializer(
            listing, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        return self._update_listing(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self._update_listing(request, *args, **kwargs)

    # ──────────────────────────────────────────────
    # Nearby Listings (custom action)
    # ──────────────────────────────────────────────

    @extend_schema(
        summary="Nearby book listings",
        description=(
            "Returns available book listings within a given radius of the specified geographic coordinates, "
            "ordered by distance (nearest first). Supports optional filtering by genre, condition, price range, "
            "and text search on book title or author name.\n\n"
            "Uses the Haversine formula for accurate distance calculation. Each returned listing includes a "
            "`distance_km` field rounded to 2 decimal places.\n\n"
            "**Performance**: A bounding-box pre-filter is applied before the Haversine calculation to minimise "
            "the number of rows processed. Future migrations to PostGIS will be straightforward."
        ),
        parameters=[
            OpenApiParameter(
                name="lat",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Latitude of the centre point (-90 to 90).",
            ),
            OpenApiParameter(
                name="lng",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Longitude of the centre point (-180 to 180).",
            ),
            OpenApiParameter(
                name="radius",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f"Search radius in kilometres (default {DEFAULT_RADIUS_KM}, max {MAX_RADIUS_KM}).",
            ),
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
            OpenApiParameter(
                name="genre",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by genre slug (e.g. 'fiction', 'exam-prep').",
            ),
            OpenApiParameter(
                name="condition",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter by book condition. One of: NEW, LIKE_NEW, GOOD, FAIR, POOR."
                ),
            ),
            OpenApiParameter(
                name="min_price",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum price filter.",
            ),
            OpenApiParameter(
                name="max_price",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum price filter.",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search by book title or author name (case-insensitive partial match).",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Order results. Options:\n"
                    "  - `distance` (default — nearest first)\n"
                    "  - `-distance` (farthest first)\n"
                    "  - `price` (lowest first)\n"
                    "  - `-price` (highest first)\n"
                    "  - `created_at` (oldest first)\n"
                    "  - `-created_at` (newest first)"
                ),
            ),
        ],
        responses={200: NearbyBookListingSerializer(many=True)},
        tags=["Book Listings"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="nearby",
        url_name="nearby-listings",
        pagination_class=NearbyListingPagination,
    )
    def nearby(self, request):
        """
        GET /api/v1/marketplace/listings/nearby/?lat=...&lng=...&radius=...

        Returns paginated available listings within the given radius, ordered
        by distance (nearest first). Each result includes a `distance_km` field.
        """
        # ── Validate required parameters ──
        lat_raw = request.query_params.get("lat")
        lng_raw = request.query_params.get("lng")

        if lat_raw is None or lng_raw is None:
            return Response(
                {"detail": "Both 'lat' and 'lng' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Parse and validate lat ──
        try:
            lat = float(lat_raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "'lat' must be a valid floating-point number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lat < -90 or lat > 90:
            return Response(
                {"detail": "'lat' must be between -90 and 90."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Parse and validate lng ──
        try:
            lng = float(lng_raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "'lng' must be a valid floating-point number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lng < -180 or lng > 180:
            return Response(
                {"detail": "'lng' must be between -180 and 180."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Parse optional radius ──
        radius_raw = request.query_params.get("radius")
        if radius_raw is not None:
            try:
                radius = float(radius_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "'radius' must be a valid floating-point number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if radius <= 0:
                return Response(
                    {"detail": "'radius' must be greater than 0."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if radius > MAX_RADIUS_KM:
                return Response(
                    {"detail": f"'radius' must not exceed {MAX_RADIUS_KM} km."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            radius = DEFAULT_RADIUS_KM

        # ── Parse optional filters ──
        genre = request.query_params.get("genre") or request.query_params.get("category")
        condition = request.query_params.get("condition")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        search = request.query_params.get("search")
        ordering = request.query_params.get("ordering", "distance")

        # ── Validate condition ──
        if condition and condition not in BookListing.Condition.values:
            return Response(
                {
                    "detail": f"Invalid 'condition'. Must be one of: {', '.join(BookListing.Condition.values)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validate ordering ──
        valid_ordering = [
            "distance",
            "-distance",
            "price",
            "-price",
            "created_at",
            "-created_at",
        ]
        if ordering not in valid_ordering:
            return Response(
                {
                    "detail": f"Invalid 'ordering'. Must be one of: {', '.join(valid_ordering)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Build queryset via service ──
        qs = get_nearby_listings(
            center_lat=lat,
            center_lng=lng,
            radius_km=radius,
            genre=genre,
            condition=condition,
            min_price=min_price,
            max_price=max_price,
            search=search,
            ordering=ordering,
        )

        # ── Annotate favorite data ──
        qs = qs.annotate(favorite_count=Count("wishlisted_by"))
        if request.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=request.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        # ── Paginate ──
        paginator = NearbyListingPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = NearbyBookListingSerializer(
                page, many=True, context={"request": request}
            )
            return paginator.get_paginated_response(serializer.data)

        # Fallback (unpaginated)
        serializer = NearbyBookListingSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List user wishlist",
        description="Retrieve all book listings saved in the current user's wishlist.",
        tags=["Wishlist"],
    ),
    create=extend_schema(
        summary="Add to wishlist",
        description="Add a book listing to the current user's wishlist.",
        request=WishlistCreateSerializer,
        responses={201: WishlistResponseSerializer},
        tags=["Wishlist"],
    ),
    destroy=extend_schema(
        summary="Remove from wishlist",
        description="Remove a book listing from the current user's wishlist.",
        tags=["Wishlist"],
    ),
)
class WishlistViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related(
            "listing", "listing__book", "listing__seller", "listing__seller__profile"
        ).prefetch_related("listing__listing_images").order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return WishlistCreateSerializer
        return WishlistResponseSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        description="Retrieve in-app notifications for the current user.",
        tags=["Notifications"],
    ),
    partial_update=extend_schema(
        summary="Mark notification as read",
        description="Mark a notification as read/unread.",
        request=PlatformNotificationSerializer,
        responses={200: PlatformNotificationSerializer},
        tags=["Notifications"],
    ),
)
class PlatformNotificationViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.UpdateModelMixin
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlatformNotificationSerializer
    queryset = PlatformNotification.objects.all()

    def get_queryset(self):
        return PlatformNotification.objects.filter(user=self.request.user).select_related(
            "related_listing", "action_trigger_user", "action_trigger_user__profile"
        )

    @action(detail=False, methods=["POST"], url_path="read-all")
    def read_all(self, request):
        PlatformNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List deal contacts ledger",
        description="Retrieve logged transactions/contacts ledger for the user.",
        tags=["Contacts Inbox"],
    ),
    create=extend_schema(
        summary="Log contact initiation",
        description="Log a deal ledger contact entry when initiating a transaction via WhatsApp.",
        request=BookContactLedgerSerializer,
        responses={201: BookContactLedgerSerializer},
        tags=["Contacts Inbox"],
    ),
)
class BookContactLedgerViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookContactLedgerSerializer

    def get_queryset(self):
        return BookContactLedger.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

