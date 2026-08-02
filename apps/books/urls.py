from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.books.views import (
    BookImportAPIView,
    BookManualCreateAPIView,
    BookSearchAPIView,
    CategoryViewSet,
    BookViewSet,
    ReviewViewSet,
    RecommendationViewSet,
    AuthorViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("books", BookViewSet, basename="book")
router.register("reviews", ReviewViewSet, basename="review")
router.register("recommendations", RecommendationViewSet, basename="recommendation")
router.register("authors", AuthorViewSet, basename="author")

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
