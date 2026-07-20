from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.serializers import (
    BookImportSerializer,
    BookManualCreateSerializer,
    BookSearchSerializer,
)
from apps.books.services import (
    create_manual_book,
    import_book_from_openlibrary,
    search_books,
)


class BookSearchAPIView(APIView):
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
        responses=BookSearchSerializer(many=True),
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
    @extend_schema(
        summary="Import book from OpenLibrary",
        description=("Imports a book using OpenLibrary work key. Accepts an optional custom category to assign if missing or unsuitable."),
        request=BookImportSerializer,
        tags=["Books"],
    )
    def post(self, request):

        serializer = BookImportSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        work_key = serializer.validated_data["openlibrary_key"]
        custom_category = serializer.validated_data.get("category")

        try:
            book, created = import_book_from_openlibrary(work_key, custom_category=custom_category)

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
    @extend_schema(
        summary="Manually insert book record",
        description="Creates a custom book catalog entry when not found in external search, including manual category assignment.",
        request=BookManualCreateSerializer,
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

