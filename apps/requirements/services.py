import math
from decimal import Decimal

from django.db import transaction
from django.db.models import FloatField, Q
from django.db.models.expressions import RawSQL

from apps.books.models import Book
from apps.marketplace.models import BookListing
from apps.marketplace.services import (
    get_bounding_box,
    haversine_distance_sql,
)
from apps.requirements.models import BookRequirement

EARTH_RADIUS_KM = 6371.0
DEFAULT_RADIUS_KM = 10.0
MAX_RADIUS_KM = 100.0

REQUIREMENT_QUERYSET = BookRequirement.objects.select_related(
    "user", "user__profile", "book"
)

_CONDITION_RANK = {
    BookListing.Condition.POOR: 0,
    BookRequirement.Condition.ACCEPTABLE: 1,
    BookListing.Condition.FAIR: 1,
    BookListing.Condition.GOOD: 2,
    BookRequirement.Condition.GOOD: 2,
    BookListing.Condition.LIKE_NEW: 3,
    BookRequirement.Condition.LIKE_NEW: 3,
    BookListing.Condition.NEW: 4,
    BookRequirement.Condition.NEW: 4,
}

_VALID_LISTING_CONDITIONS_FOR_REQUIREMENT = {
    req_cond: [
        c for c, r in _CONDITION_RANK.items()
        if r >= _CONDITION_RANK.get(req_cond, -1)
        and c in BookListing.Condition.values
    ]
    for req_cond in BookRequirement.Condition.values
}


def create_requirement(
    *,
    user,
    book_title,
    preferred_condition,
    min_price=None,
    max_price=None,
    notes="",
    book=None,
    latitude=None,
    longitude=None,
):
    with transaction.atomic():
        requirement = BookRequirement.objects.create(
            user=user,
            book=book,
            book_title=book_title.strip(),
            preferred_condition=preferred_condition,
            min_price=min_price,
            max_price=max_price,
            notes=notes or "",
            latitude=latitude,
            longitude=longitude,
        )
    return requirement


def get_active_requirements():
    return REQUIREMENT_QUERYSET.filter(
        status=BookRequirement.Status.ACTIVE
    ).order_by("-created_at")


def get_requirements_for_user(*, user):
    return REQUIREMENT_QUERYSET.filter(user=user).order_by("-created_at")


def get_requirement_by_id(*, requirement_id):
    return REQUIREMENT_QUERYSET.get(pk=requirement_id)


def update_requirement(*, requirement, data):
    update_fields = []

    if "book_title" in data:
        requirement.book_title = data["book_title"].strip()
        update_fields.append("book_title")
    if "preferred_condition" in data:
        requirement.preferred_condition = data["preferred_condition"]
        update_fields.append("preferred_condition")
    if "min_price" in data:
        requirement.min_price = data["min_price"]
        update_fields.append("min_price")
    if "max_price" in data:
        requirement.max_price = data["max_price"]
        update_fields.append("max_price")
    if "notes" in data:
        requirement.notes = data["notes"]
        update_fields.append("notes")
    if "status" in data:
        requirement.status = data["status"]
        update_fields.append("status")
    if "book" in data:
        requirement.book = data["book"]
        update_fields.append("book")
    if "latitude" in data:
        requirement.latitude = data["latitude"]
        update_fields.append("latitude")
    if "longitude" in data:
        requirement.longitude = data["longitude"]
        update_fields.append("longitude")

    if update_fields:
        update_fields.append("updated_at")
        requirement.save(update_fields=update_fields)

    return requirement


def find_matching_requirements(requirement):
    """
    Return a queryset of AVAILABLE listings matching the given requirement.

    Matching rules:
    1. Book match: use Book FK if available, otherwise title similarity.
    2. Condition compatible: listing condition rank >= required condition rank.
    3. Price compatible: listing price within requirement's min/max.
    4. Listing status must be AVAILABLE.
    5. Seller must NOT be the requirement owner.

    This service is the single source of truth for matching logic and will be
    reused by Notifications, Recommendations, Home Feed, and Admin Dashboard.
    """
    qs = BookListing.objects.select_related(
        "book", "seller", "seller__profile"
    ).filter(
        status=BookListing.Status.AVAILABLE,
    ).exclude(seller=requirement.user)

    if requirement.book:
        qs = qs.filter(book=requirement.book)
    elif requirement.book_title:
        qs = qs.filter(book__title__iexact=requirement.book_title.strip())

    if requirement.preferred_condition:
        valid_conditions = _VALID_LISTING_CONDITIONS_FOR_REQUIREMENT.get(
            requirement.preferred_condition, []
        )
        if valid_conditions:
            qs = qs.filter(condition__in=valid_conditions)

    if requirement.min_price is not None:
        qs = qs.filter(price__gte=requirement.min_price)
    if requirement.max_price is not None:
        qs = qs.filter(price__lte=requirement.max_price)

    return qs


def get_nearby_requirements(
    center_lat,
    center_lng,
    radius_km=DEFAULT_RADIUS_KM,
    search=None,
    condition=None,
    min_price=None,
    max_price=None,
    ordering="distance",
):
    """
    Return a queryset of ACTIVE requirements within `radius_km` of
    (center_lat, center_lng), annotated with `distance_km`.

    Performance strategy mirrors the marketplace nearby endpoint:
      1. Filter status=ACTIVE and non-null coordinates (cheap).
      2. Apply optional filters before expensive distance calculation.
      3. Bounding-box pre-filter to reduce rows.
      4. Annotate with Haversine distance.
      5. Filter by radius and order.
    """
    qs = BookRequirement.objects.select_related(
        "user", "user__profile", "book"
    )

    qs = qs.filter(
        status=BookRequirement.Status.ACTIVE,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    if search:
        qs = qs.filter(
            Q(book_title__icontains=search)
            | Q(book__title__icontains=search)
        ).distinct()

    if condition:
        if condition in BookRequirement.Condition.values:
            qs = qs.filter(preferred_condition=condition)

    if min_price is not None:
        try:
            qs = qs.filter(min_price__gte=Decimal(str(min_price)))
        except Exception:
            pass

    if max_price is not None:
        try:
            qs = qs.filter(max_price__lte=Decimal(str(max_price)))
        except Exception:
            pass

    min_lat, max_lat, min_lng, max_lng = get_bounding_box(
        center_lat, center_lng, radius_km
    )
    qs = qs.filter(
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lng,
        longitude__lte=max_lng,
    )

    table = BookRequirement._meta.db_table

    distance_expr = haversine_distance_sql(
        f"{table}.latitude",
        f"{table}.longitude",
        center_lat, center_lng
    )
    qs = qs.annotate(distance_km=distance_expr)
    qs = qs.filter(distance_km__lte=radius_km)

    if ordering == "distance":
        qs = qs.order_by("distance_km")
    elif ordering == "-distance":
        qs = qs.order_by("-distance_km")
    elif ordering == "created_at":
        qs = qs.order_by("created_at")
    elif ordering == "-created_at":
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("distance_km")

    return qs
