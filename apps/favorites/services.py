from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Value, BooleanField

from apps.authentication.models import User
from apps.marketplace.models import BookListing, Wishlist


def add_favorite(user: User, listing_id: int) -> Wishlist:
    """
    Add a listing to user's favorites.

    Business rules:
    - User cannot favorite their own listing.
    - Listing must be AVAILABLE.
    - Duplicate favorites return an error.
    """
    try:
        listing = BookListing.objects.get(pk=listing_id)
    except BookListing.DoesNotExist:
        raise ValueError("Listing not found.")

    if listing.seller == user:
        raise ValueError("Cannot favorite your own listing.")

    if listing.status != BookListing.Status.AVAILABLE:
        raise ValueError("Cannot favorite a listing that is not available.")

    favorite, created = Wishlist.objects.get_or_create(
        user=user,
        listing=listing,
    )

    if not created:
        raise ValueError("Listing is already in your favorites.")

    return favorite


def remove_favorite(user: User, listing_id: int) -> int:
    """
    Remove a listing from user's favorites.

    Returns the number of deleted rows (0 or 1).
    """
    deleted, _ = Wishlist.objects.filter(
        user=user,
        listing_id=listing_id,
    ).delete()

    if deleted == 0:
        raise ValueError("Listing not in favorites.")

    return deleted


def list_favorites(user: User):
    """
    Return a queryset of BookListings favorited by the user,
    ordered by newest saved first.
    """
    return (
        BookListing.objects.filter(wishlisted_by__user=user)
        .select_related("book", "seller", "seller__profile")
        .prefetch_related("book__authors", "listing_images")
        .annotate(
            favorite_count=Count("wishlisted_by"),
            is_favorited=Value(True),
        )
        .order_by("-wishlisted_by__created_at")
    )


def is_favorited(user: User, listing_id: int) -> bool:
    """
    Return True if the user has favorited the listing.
    Anonymous users always return False.
    """
    if not user.is_authenticated:
        return False
    return Wishlist.objects.filter(
        user=user,
        listing_id=listing_id,
    ).exists()


def favorite_count(listing_id: int) -> int:
    """
    Return the total number of users who have favorited the listing.
    """
    return Wishlist.objects.filter(listing_id=listing_id).count()
