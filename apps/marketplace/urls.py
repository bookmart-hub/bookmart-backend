from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.marketplace.views import (
    BookListingViewSet,
    WishlistViewSet,
    PlatformNotificationViewSet,
    BookContactLedgerViewSet,
)

router = DefaultRouter()
router.register("listings", BookListingViewSet, basename="book-listing")
router.register("wishlist", WishlistViewSet, basename="wishlist")
router.register("notifications", PlatformNotificationViewSet, basename="notification")
router.register("contacts", BookContactLedgerViewSet, basename="contact-ledger")

urlpatterns = [
    path("", include(router.urls)),
]
