from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, permissions, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.marketplace.models import BookListing
from apps.marketplace.serializers import (
    BookListingCreateSerializer,
    BookListingResponseSerializer,
)
from apps.marketplace.services import create_book_listing


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
        description="Full update of an existing book listing.",
        tags=["Book Listings"],
    ),
    partial_update=extend_schema(
        summary="Partially update a book listing",
        description="Partial update of an existing book listing.",
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
        # Optimized with select_related and prefetch_related for high performance
        return (
            BookListing.objects.select_related("book", "seller", "seller__profile")
            .prefetch_related("book__authors", "listing_images")
            .all()
        )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return BookListingCreateSerializer
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

