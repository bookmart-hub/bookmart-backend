from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.books.views import (
    BookImportAPIView,
    BookManualCreateAPIView,
    BookSearchAPIView,
    CategoryViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
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
