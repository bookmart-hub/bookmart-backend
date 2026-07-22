from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.models import Book, Category
from apps.books.serializers import (
    BookCreatedResponseSerializer,
    BookImportSerializer,
    BookManualCreateSerializer,
    BookSearchSerializer,
    CategoryDetailSerializer,
    CategoryListSerializer,
)
from apps.books.services import (
    create_manual_book,
    import_book_from_openlibrary,
    search_books,
)
from apps.marketplace.models import BookListing


@extend_schema_view(
    list=extend_schema(
        summary="List all book categories",
        description="Retrieve all available book categories with icon, subtitle, and total books count.",
        responses={200: CategoryListSerializer(many=True)},
        tags=["Categories"],
    ),
    retrieve=extend_schema(
        summary="Retrieve category details and price-ranked books",
        description="Fetch category details by ID or slug. Returns all canonical books in this category with active listings ranked by price ascending (cheapest first).",
        # parameters=[
        #     OpenApiParameter(
        #         name="pk",
        #         type=str,
        #         location=OpenApiParameter.PATH,
        #         description="Category ID (e.g. 1) or Category Slug (e.g. 'competitive-exams').",
        #     )
        # ],
        responses={200: CategoryDetailSerializer},
        tags=["Categories"],
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for browsing and retrieving book categories and category screens.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Category.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CategoryDetailSerializer
        return CategoryListSerializer

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
                "categories",
                Prefetch(
                    "listings",
                    queryset=available_listings_qs,
                    to_attr="ranked_listings",
                ),
            ).distinct(),
            to_attr="category_books",
        )

        if str(lookup_value).isdigit():
            category = get_object_or_404(
                Category.objects.prefetch_related(books_prefetch),
                pk=int(lookup_value),
            )
        else:
            category = get_object_or_404(
                Category.objects.prefetch_related(books_prefetch),
                slug=lookup_value,
            )

        return category


class BookSearchAPIView(APIView):
    serializer_class = BookSearchSerializer

    @extend_schema(
        summary="Search books (local catalog and OpenLibrary)",
        description="Search books by title, author, ISBN, etc. Returns local matching books as well as external OpenLibrary results.",
        parameters=[
            OpenApiParameter(
                name="q",
                description="Search query",
                required=True,
                type=str,
            )
        ],
        responses={200: BookSearchSerializer(many=True)},
        tags=["Books"],
    )
    def get(self, request):

        query = request.GET.get("q")

        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        books = search_books(query)

        serializer = BookSearchSerializer(books, many=True)

        return Response(serializer.data)


class BookImportAPIView(APIView):
    serializer_class = BookImportSerializer

    @extend_schema(
        summary="Import book from OpenLibrary",
        description=(
            "Imports a book using OpenLibrary work key. Accepts an optional custom category to assign if missing or unsuitable."
        ),
        request=BookImportSerializer,
        responses={
            200: BookCreatedResponseSerializer,
            201: BookCreatedResponseSerializer,
        },
        tags=["Books"],
    )
    def post(self, request):

        serializer = BookImportSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        work_key = serializer.validated_data["openlibrary_key"]
        custom_category = serializer.validated_data.get("category")

        try:
            book, created = import_book_from_openlibrary(
                work_key, custom_category=custom_category
            )

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "created": created,
                "book_id": book.id,
                "title": book.title,
                "cover_url": book.cover_url,
                "published_year": (
                    book.published_date.year if book.published_date else None
                ),
                "authors": [author.name for author in book.authors.all()],
                "categories": [category.name for category in book.categories.all()],
                "is_local": True,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BookManualCreateAPIView(APIView):
    serializer_class = BookManualCreateSerializer

    @extend_schema(
        summary="Manually insert book record",
        description="Creates a custom book catalog entry when not found in external search, including manual category assignment.",
        request=BookManualCreateSerializer,
        responses={201: BookCreatedResponseSerializer},
        tags=["Books"],
    )
    def post(self, request):
        serializer = BookManualCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            book = create_manual_book(serializer.validated_data)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "created": True,
                "book_id": book.id,
                "title": book.title,
                "cover_url": book.cover_url,
                "published_year": (
                    book.published_date.year if book.published_date else None
                ),
                "authors": [author.name for author in book.authors.all()],
                "categories": [category.name for category in book.categories.all()],
                "is_local": True,
            },
            status=status.HTTP_201_CREATED,
        )
