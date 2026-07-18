from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.marketplace.views import BookListingViewSet

router = DefaultRouter()
router.register("listings", BookListingViewSet, basename="book-listing")

urlpatterns = [
    path("", include(router.urls)),
]
