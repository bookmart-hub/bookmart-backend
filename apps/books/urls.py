from django.urls import path

from apps.books.views import BookImportAPIView, BookSearchAPIView

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
]
