from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, permissions, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.marketplace.models import BookListing
from apps.marketplace.serializers import (
    BookListingCreateSerializer,
    BookListingResponseSerializer,
    BookListingUpdateSerializer,
)
from apps.marketplace.services import create_book_listing, update_book_listing


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
    filterset_fields = ["condition", "status", "book"]
    ordering_fields = ["price", "created_at"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_queryset(self):
        return (
            BookListing.objects.select_related("book", "seller", "seller__profile")
            .prefetch_related("book__authors", "listing_images")
            .all()
        )

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

