from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.marketplace.views import BookListingImageViewSet, BookListingViewSet

router = DefaultRouter()
router.register("listings", BookListingViewSet, basename="book-listing")
router.register(
    "listing-images", BookListingImageViewSet, basename="book-listing-image"
)

urlpatterns = [
    path("", include(router.urls)),
]
