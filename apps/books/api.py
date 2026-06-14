from typing import List, Optional
from ninja import Router, Schema
from django.db.models import Q
from apps.books.models import Listing, Book

router = Router(tags=["Marketplace"])

# --- Schemas ---


class UserMinOut(Schema):
    id: int
    full_name: str


class BookOut(Schema):
    id: int
    isbn_13: str
    title: str
    authors: List[str]
    cover_image_url: str | None


class ListingOut(Schema):
    id: int
    book: BookOut
    seller: UserMinOut
    price: float
    condition: str
    condition_description: str | None
    images: List[str]
    created_at: str

# --- Endpoints ---


@router.get("/listings", response=List[ListingOut])
def list_marketplace_books(
    request,
    search: Optional[str] = None,
    max_price: Optional[float] = None,
    condition: Optional[str] = None
):
    """
    High-performance, optimized query pool fetching active used book listings.
    """
    # Base filter: Only show books currently available for purchase
    queryset = Listing.objects.filter(status='AVAILABLE')

    if search:
        # Complex Q-object evaluation looking up against Title, Authors array, or ISBN
        queryset = queryset.filter(
            Q(book__title__icontains=search) |
            Q(book__authors__icontains=search) |
            Q(book__isbn_13=search)
        )

    if max_price:
        queryset = queryset.filter(price__lte=max_price)

    if condition:
        queryset = queryset.filter(condition=condition)

    # CRITICAL MASTERSTROKE: Optimize database performance via select_related
    # This avoids the N+1 query issue by executing a single SQL JOIN operation.
    queryset = queryset.select_related(
        'book', 'seller').order_by('-created_at')[:20]

    return queryset
