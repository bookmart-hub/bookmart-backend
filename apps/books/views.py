from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.models import Book, Genre, Review, Author
from apps.books.serializers import (
    BookCreatedResponseSerializer,
    BookImportSerializer,
    BookManualCreateSerializer,
    BookSearchSerializer,
    GenreDetailSerializer,
    GenreListSerializer,
    CanonicalBookGenreSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
    AuthorSerializer,
)
from apps.books.services import (
    create_manual_book,
    import_book_from_openlibrary,
    search_books,
)
from apps.marketplace.models import BookListing


@extend_schema_view(
    list=extend_schema(
        summary="List all book genres",
        description="Retrieve all available book genres with icon, subtitle, and total books count.",
        responses={200: GenreListSerializer(many=True)},
        tags=["Genres"],
    ),
    retrieve=extend_schema(
        summary="Retrieve genre details and price-ranked books",
        description="Fetch genre details by ID or slug. Returns all canonical books in this genre with active listings ranked by price ascending (cheapest first).",
        responses={200: GenreDetailSerializer},
        tags=["Genres"],
    ),
)
class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for browsing and retrieving book genres.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Genre.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GenreDetailSerializer
        return GenreListSerializer

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_field or "pk")

        available_listings_qs = (
            BookListing.objects.filter(status="AVAILABLE")
            .order_by("price")
            .select_related("seller", "seller__profile")
            .prefetch_related("listing_images")
        )

        books_prefetch = Prefetch(
            "books",
            queryset=Book.objects.prefetch_related(
                "authors",
                "genres",
                Prefetch(
                    "listings",
                    queryset=available_listings_qs,
                    to_attr="ranked_listings",
                ),
            ).distinct(),
            to_attr="genre_books",
        )

        if str(lookup_value).isdigit():
            genre = get_object_or_404(
                Genre.objects.prefetch_related(books_prefetch),
                pk=int(lookup_value),
            )
        else:
            genre = get_object_or_404(
                Genre.objects.prefetch_related(books_prefetch),
                slug=lookup_value,
            )

        return genre


class BookImportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Import book from OpenLibrary",
        description="Search OpenLibrary by work key and import/create local catalog entry if not exists.",
        request=BookImportSerializer,
        responses={
            201: BookCreatedResponseSerializer,
            200: BookCreatedResponseSerializer,
        },
        tags=["Catalog Import"],
    )
    def post(self, request):
        serializer = BookImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ol_key = serializer.validated_data["openlibrary_key"]
        genre_val = serializer.validated_data.get("genre")

        book, created = import_book_from_openlibrary(ol_key, custom_category=genre_val)

        return Response(
            {
                "created": created,
                "book_id": book.id,
                "title": book.title,
                "cover_url": book.cover_url or None,
                "published_year": book.published_date.year if book.published_date else None,
                "authors": [author.name for author in book.authors.all()],
                "genres": [genre.name for genre in book.genres.all()],
                "is_local": True,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BookSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Search books (local + fallback OpenLibrary)",
        description="Search books by title, author, or ISBN. Returns local matches if found, otherwise queries OpenLibrary search endpoint.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                required=True,
                location=OpenApiParameter.QUERY,
                description="Search query term (title, author, or isbn)",
            )
        ],
        responses={200: BookSearchSerializer(many=True)},
        tags=["Books"],
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query.strip():
            return Response([])

        results = search_books(query)
        # Rename categories to genres in search response
        for r in results:
            r["genres"] = r.pop("categories", [])
        return Response(results)


class BookManualCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Manually create a catalog book entry",
        description="Create a custom book record in the catalog when not available via OpenLibrary search.",
        request=BookManualCreateSerializer,
        responses={201: BookCreatedResponseSerializer},
        tags=["Catalog Import"],
    )
    def post(self, request):
        serializer = BookManualCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book = create_manual_book(serializer.validated_data)

        return Response(
            {
                "created": True,
                "book_id": book.id,
                "title": book.title,
                "cover_url": book.cover_url or None,
                "published_year": book.published_date.year if book.published_date else None,
                "authors": [author.name for author in book.authors.all()],
                "genres": [genre.name for genre in book.genres.all()],
                "is_local": True,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(
        summary="List all catalog books",
        description="Retrieve a paginated list of all canonical catalog books. Supports filtering by genre (slug or ID) and searching by title, author, or ISBN.",
        tags=["Books"],
    ),
    retrieve=extend_schema(
        summary="Retrieve catalog book details",
        description="Fetch a single catalog book by ID, including its available marketplace listings.",
        tags=["Books"],
    ),
)
class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for browsing and retrieving canonical catalog books.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = CanonicalBookGenreSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["genres", "genres__slug"]
    search_fields = ["title", "authors__name", "isbn_13", "isbn_10"]
    ordering_fields = ["created_at", "title"]

    def get_queryset(self):
        available_listings_qs = (
            BookListing.objects.filter(status="AVAILABLE")
            .order_by("price")
            .select_related("seller", "seller__profile")
            .prefetch_related("listing_images")
        )
        return (
            Book.objects.prefetch_related(
                "authors",
                "genres",
                Prefetch(
                    "listings",
                    queryset=available_listings_qs,
                    to_attr="ranked_listings",
                ),
            )
            .all()
            .distinct()
        )


@extend_schema_view(
    list=extend_schema(
        summary="List book reviews",
        description="Retrieve a paginated list of all book reviews.",
        tags=["Reviews"],
    ),
    create=extend_schema(
        summary="Create a new book review",
        description="Submit a rating (1-5) and feedback comment for a canonical catalog book.",
        request=ReviewCreateSerializer,
        responses={201: ReviewSerializer},
        tags=["Reviews"],
    ),
)
class ReviewViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Review.objects.all().select_related("user").order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ReviewCreateSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List book recommendations",
        description="Retrieve recommended books based on available listings.",
        tags=["Recommendations"],
    ),
)
class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for displaying book recommendations.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = CanonicalBookGenreSerializer

    def get_queryset(self):
        available_listings_qs = (
            BookListing.objects.filter(status="AVAILABLE")
            .order_by("price")
            .select_related("seller", "seller__profile")
            .prefetch_related("listing_images")
        )
        return (
            Book.objects.filter(listings__status="AVAILABLE")
            .prefetch_related(
                "authors",
                "genres",
                Prefetch(
                    "listings",
                    queryset=available_listings_qs,
                    to_attr="ranked_listings",
                ),
            )
            .distinct()
        )


@extend_schema_view(
    list=extend_schema(
        summary="List authors",
        description="Retrieve all authors in the master catalog.",
        tags=["Authors"],
    ),
    retrieve=extend_schema(
        summary="Retrieve author details",
        description="Fetch a single author details by ID, including their catalog books.",
        tags=["Authors"],
    ),
)
class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Author.objects.all().order_by("name")
    serializer_class = AuthorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]
