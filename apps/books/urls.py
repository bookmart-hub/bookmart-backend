from django.urls import path

from apps.books.views import (
    BookImportAPIView,
    BookManualCreateAPIView,
    BookSearchAPIView,
)

urlpatterns = [
    path(
        "search/",
        BookSearchAPIView.as_view(),
        name="book-search",
    ),
    path(
        "import-openlibrary/",
        BookImportAPIView.as_view(),
        name="import-openlibrary",
    ),
    path(
        "manual/",
        BookManualCreateAPIView.as_view(),
        name="book-manual-create",
    ),
]

