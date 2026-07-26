import math
from decimal import Decimal

from django.db import transaction
from django.db.models import FloatField, Q
from django.db.models.expressions import RawSQL

from apps.books.models import Author, Book
from apps.books.services import import_book_from_openlibrary, process_category_input
from apps.marketplace.models import BookListing, BookListingImage


# ──────────────────────────────────────────────
# Constants for Earth's radius (in kilometers)
# ──────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0
MAX_RADIUS_KM = 100.0
DEFAULT_RADIUS_KM = 10.0


def haversine_distance_sql(lat_field, lng_field, center_lat, center_lng):
    """
    Returns a RawSQL expression that computes the Haversine distance in km
    between a row's (lat_field, lng_field) and a fixed (center_lat, center_lng).

    This expression is database-agnostic and can be replaced with PostGIS
    ST_Distance(geography) in the future for better performance.

    Uses parameterized center coordinates (in degrees) to avoid SQL injection
    and ensure proper quoting.
    """
    center_lat = float(center_lat)
    center_lng = float(center_lng)

    # Use parameterized SQL to safely pass center coordinates (in degrees).
    # RADIANS() converts degrees to radians inside PostgreSQL.
    sql = f"""
        {EARTH_RADIUS_KM} * 2 * ASIN(
            SQRT(
                POWER(SIN(RADIANS(COALESCE({lat_field}, 0) - %s) / 2), 2)
                + COS(RADIANS(%s))
                * COS(RADIANS(COALESCE({lat_field}, 0)))
                * POWER(SIN(RADIANS(COALESCE({lng_field}, 0) - %s) / 2), 2)
            )
        )
    """
    return RawSQL(sql, (center_lat, center_lat, center_lng), output_field=FloatField())


def get_bounding_box(lat, lng, radius_km):
    """
    Calculate a bounding box (min_lat, max_lat, min_lng, max_lng)
    for a given center point and radius.

    This is used to pre-filter listings before the more expensive
    Haversine calculation, improving query performance.
    """
    lat = float(lat)
    lng = float(lng)
    radius_km = float(radius_km)

    # Latitude: 1 degree ≈ 111 km
    lat_delta = radius_km / 111.0
    min_lat = lat - lat_delta
    max_lat = lat + lat_delta

    # Longitude: 1 degree ≈ 111 * cos(lat) km
    lng_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    min_lng = lng - lng_delta
    max_lng = lng + lng_delta

    return min_lat, max_lat, min_lng, max_lng


def get_nearby_listings(
    center_lat,
    center_lng,
    radius_km=DEFAULT_RADIUS_KM,
    category=None,
    condition=None,
    min_price=None,
    max_price=None,
    search=None,
    ordering="distance",
):
    """
    Return a queryset of available BookListings within `radius_km` of
    (center_lat, center_lng), ordered by distance (nearest first).

    Performance strategy:
      1. Filter status=AVAILABLE and exclude null coordinates (cheap).
      2. Apply optional filters (category, condition, price, search) before
         the expensive Haversine calculation whenever possible.
      3. Apply a bounding-box pre-filter to reduce rows before Haversine.
      4. Annotate each row with Haversine distance.
      5. Filter by radius.
      6. Order as requested.

    Future compatibility:
      - Bounding box: already implemented as a pre-filter.
      - PostGIS: replace `haversine_distance_sql()` with
        `ST_DistanceSphere(ST_MakePoint(...), ST_MakePoint(...))`.
      - Search this area: the `search` param already supports title/author.
      - Map clustering: distance_km is annotated, enabling easy aggregation.
    """
    # --- Step 1: Base filter ---
    qs = BookListing.objects.select_related(
        "book", "seller", "seller__profile"
    ).prefetch_related("book__authors", "listing_images")

    # --- Step 2: Status and coordinate existence (cheapest filters first) ---
    qs = qs.filter(
        status=BookListing.Status.AVAILABLE,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    # --- Step 3: Optional filters (before distance calculation) ---
    if condition:
        if condition in BookListing.Condition.values:
            qs = qs.filter(condition=condition)

    if min_price is not None:
        try:
            qs = qs.filter(price__gte=Decimal(str(min_price)))
        except Exception:
            pass

    if max_price is not None:
        try:
            qs = qs.filter(price__lte=Decimal(str(max_price)))
        except Exception:
            pass

    if category:
        qs = qs.filter(book__categories__slug=category)

    if search:
        qs = qs.filter(
            Q(book__title__icontains=search)
            | Q(book__authors__name__icontains=search)
        ).distinct()

    # --- Step 4: Bounding-box pre-filter (reduces rows before Haversine) ---
    min_lat, max_lat, min_lng, max_lng = get_bounding_box(
        center_lat, center_lng, radius_km
    )
    qs = qs.filter(
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lng,
        longitude__lte=max_lng,
    )

    # --- Step 5: Annotate with Haversine distance ---
    distance_expr = haversine_distance_sql(
        "latitude", "longitude", center_lat, center_lng
    )
    qs = qs.annotate(distance_km=distance_expr)

    # --- Step 6: Filter by actual Haversine radius ---
    qs = qs.filter(distance_km__lte=radius_km)

    # --- Step 7: Ordering ---
    if ordering == "price":
        qs = qs.order_by("price")
    elif ordering == "-price":
        qs = qs.order_by("-price")
    elif ordering == "created_at":
        qs = qs.order_by("created_at")
    elif ordering == "-created_at":
        qs = qs.order_by("-created_at")
    elif ordering == "distance":
        qs = qs.order_by("distance_km")
    elif ordering == "-distance":
        qs = qs.order_by("-distance_km")
    else:
        # Default: nearest first
        qs = qs.order_by("distance_km")

    return qs


@transaction.atomic
def create_book_listing(seller, data):
    book_id = data.get("book_id")
    openlibrary_key = data.get("openlibrary_key")
    title = data.get("title")
    author_name = data.get("author")
    custom_category = data.get("category") or data.get("categories")

    book = None

    if book_id:
        book = Book.objects.get(id=book_id)
    elif openlibrary_key:
        book = Book.objects.filter(openlibrary_key=openlibrary_key).first()
        if not book:
            book, _ = import_book_from_openlibrary(openlibrary_key, custom_category=custom_category)
    elif title and author_name:
        book = Book.objects.filter(
            title__iexact=title.strip(),
            authors__name__iexact=author_name.strip(),
        ).first()

        if not book:
            author, _ = Author.objects.get_or_create(name=author_name.strip())
            book = Book.objects.create(
                title=title.strip(),
            )
            book.authors.add(author)

    if book and custom_category:
        cats = process_category_input(custom_category)
        if cats:
            book.categories.add(*cats)

    listing = BookListing.objects.create(
        book=book,
        seller=seller,
        price=data["price"],
        condition=data["condition"],
        condition_notes=data.get("condition_notes", ""),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )

    image_fields = {
        "front_cover": BookListingImage.ImageLabel.FRONT_COVER,
        "back_cover": BookListingImage.ImageLabel.BACK_COVER,
        "spine": BookListingImage.ImageLabel.SPINE,
        "middle_page": BookListingImage.ImageLabel.MIDDLE_PAGE,
        "damage_1": BookListingImage.ImageLabel.DAMAGE_1,
        "damage_2": BookListingImage.ImageLabel.DAMAGE_2,
    }

    for field_name, label in image_fields.items():
        file_obj = data.get(field_name)
        if file_obj:
            BookListingImage.objects.create(
                book_listing=listing,
                image=file_obj,
                label=label,
            )

    return listing


@transaction.atomic
def update_book_listing(listing, user, data):
    if listing.seller != user:
        raise PermissionError("You do not own this listing.")

    book_id = data.get("book_id")
    openlibrary_key = data.get("openlibrary_key")
    title = data.get("title")
    author_name = data.get("author")

    if any([book_id, openlibrary_key, title, author_name]):
        book = None

        if book_id:
            book = Book.objects.get(id=book_id)
        elif openlibrary_key:
            book = Book.objects.filter(openlibrary_key=openlibrary_key).first()
            if not book:
                custom_category = data.get("category") or data.get("categories")
                book, _ = import_book_from_openlibrary(
                    openlibrary_key, custom_category=custom_category
                )
        elif title and author_name:
            book = Book.objects.filter(
                title__iexact=title.strip(),
                authors__name__iexact=author_name.strip(),
            ).first()

            if not book:
                author, _ = Author.objects.get_or_create(name=author_name.strip())
                book = Book.objects.create(title=title.strip())
                book.authors.add(author)

        if book:
            custom_category = data.get("category") or data.get("categories")
            if custom_category:
                cats = process_category_input(custom_category)
                if cats:
                    book.categories.add(*cats)
            listing.book = book

    listing.price = data.get("price", listing.price)
    listing.condition = data.get("condition", listing.condition)
    listing.condition_notes = data.get("condition_notes", listing.condition_notes)
    listing.status = data.get("status", listing.status)
    listing.latitude = data.get("latitude", listing.latitude)
    listing.longitude = data.get("longitude", listing.longitude)
    listing.save()

    removed_ids = data.get("removed_image_ids", [])
    if removed_ids:
        BookListingImage.objects.filter(
            id__in=removed_ids,
            book_listing=listing,
        ).delete()

    image_fields = {
        "front_cover": BookListingImage.ImageLabel.FRONT_COVER,
        "back_cover": BookListingImage.ImageLabel.BACK_COVER,
        "spine": BookListingImage.ImageLabel.SPINE,
        "middle_page": BookListingImage.ImageLabel.MIDDLE_PAGE,
        "damage_1": BookListingImage.ImageLabel.DAMAGE_1,
        "damage_2": BookListingImage.ImageLabel.DAMAGE_2,
    }

    for field_name, label in image_fields.items():
        file_obj = data.get(field_name)
        if file_obj is not None:
            BookListingImage.objects.filter(
                book_listing=listing,
                label=label,
            ).delete()
            BookListingImage.objects.create(
                book_listing=listing,
                image=file_obj,
                label=label,
            )

    return listing
