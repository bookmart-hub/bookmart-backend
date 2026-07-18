from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.serializers import (
    BookImportSerializer,
    BookSearchSerializer,
)
from apps.books.services import (
    import_book_from_openlibrary,
    search_books,
)


class BookSearchAPIView(APIView):
    @extend_schema(
        summary="Search books from OpenLibrary",
        description="Search books by title, author, ISBN, etc.",
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
        description=("Imports a book using OpenLibrary work key."),
        request=BookImportSerializer,
        tags=["Books"],
    )
    def post(self, request):

        serializer = BookImportSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        work_key = serializer.validated_data["openlibrary_key"]

        try:
            book, created = import_book_from_openlibrary(work_key)

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
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
