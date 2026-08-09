from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q, Subquery, Value, BooleanField, IntegerField
from django.db.models.functions import Coalesce

from apps.books.models import Book, Genre
from apps.books.serializers import GenreListSerializer
from apps.marketplace.models import BookListing, BookListingImage, Wishlist
from apps.marketplace.services import get_bounding_box, haversine_distance_sql
from apps.requirements.models import BookRequirement

User = get_user_model()

MAX_SECTION_SIZE = 15
DEFAULT_PAGE_SIZE = 10
NEARBY_MAX = 10
FEATURED_MAX = 10


class HomeFeedService:
    def __init__(self, user, lat=None, lng=None, radius=None, page_size=None):
        self.user = user
        self.lat = lat
        self.lng = lng
        self.radius = radius or 10.0
        self.page_size = min(page_size or DEFAULT_PAGE_SIZE, MAX_SECTION_SIZE)

    def get_nearby_books(self):
        if self.lat is None or self.lng is None:
            return BookListing.objects.none()

        table = BookListing._meta.db_table
        qs = BookListing.objects.select_related(
            "book", "seller", "seller__profile"
        ).prefetch_related("book__authors", "listing_images")

        qs = qs.filter(
            status=BookListing.Status.AVAILABLE,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        min_lat, max_lat, min_lng, max_lng = get_bounding_box(
            self.lat, self.lng, self.radius
        )
        qs = qs.filter(
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lng,
            longitude__lte=max_lng,
        )

        distance_expr = haversine_distance_sql(
            f"{table}.latitude",
            f"{table}.longitude",
            self.lat,
            self.lng,
        )
        qs = qs.annotate(distance_km=distance_expr)
        qs = qs.filter(distance_km__lte=self.radius)
        qs = qs.order_by("distance_km")

        qs = qs.annotate(
            favorite_count=Count("wishlisted_by"),
        )

        if self.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=self.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        return qs[:NEARBY_MAX]

    def get_latest_books(self):
        qs = BookListing.objects.select_related(
            "book", "seller", "seller__profile"
        ).prefetch_related("book__authors", "listing_images")

        qs = qs.filter(status=BookListing.Status.AVAILABLE)

        qs = qs.annotate(
            favorite_count=Count("wishlisted_by"),
        )

        if self.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=self.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        return qs.order_by("-created_at")[:self.page_size]

    def get_popular_books(self):
        qs = BookListing.objects.select_related(
            "book", "seller", "seller__profile"
        ).prefetch_related("book__authors", "listing_images")

        qs = qs.filter(status=BookListing.Status.AVAILABLE)

        qs = qs.annotate(
            favorite_count=Count("wishlisted_by"),
        )

        if self.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=self.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        qs = qs.order_by("-favorite_count", "-created_at")

        return qs[:self.page_size]

    def get_featured_books(self):
        qs = BookListing.objects.select_related(
            "book", "seller", "seller__profile"
        ).prefetch_related("book__authors", "listing_images")

        qs = qs.filter(
            status=BookListing.Status.AVAILABLE,
            condition__in=[
                BookListing.Condition.NEW,
                BookListing.Condition.LIKE_NEW,
                BookListing.Condition.GOOD,
            ],
        )

        qs = qs.annotate(
            image_count=Count("listing_images"),
        ).filter(image_count__gte=4)

        qs = qs.annotate(
            favorite_count=Count("wishlisted_by"),
        )

        if self.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=self.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        return qs.order_by("-created_at")[:FEATURED_MAX]

    def get_recommended_books(self):
        if not self.user.is_authenticated:
            return self.get_latest_books()

        user_listing_book_ids = list(
            BookListing.objects.filter(seller=self.user)
            .values_list("book_id", flat=True)
        )

        user_favorite_book_ids = list(
            Wishlist.objects.filter(user=self.user)
            .values_list("listing__book_id", flat=True)
        )

        user_requirement_book_ids = list(
            BookRequirement.objects.filter(user=self.user)
            .values_list("book_id", flat=True)
        )

        interacted_book_ids = set(user_listing_book_ids) | set(user_favorite_book_ids) | set(user_requirement_book_ids)

        if not interacted_book_ids:
            return self.get_latest_books()

        interacted_books = Book.objects.filter(id__in=interacted_book_ids)
        interacted_genre_ids = list(
            interacted_books.values_list("genres", flat=True)
        )

        interacted_author_ids = list(
            interacted_books.values_list("authors", flat=True)
        )

        similar_titles = list(
            interacted_books.values_list("title", flat=True)
        )

        genre_books = Book.objects.filter(
            genres__id__in=interacted_genre_ids
        ).distinct()

        author_books = Book.objects.filter(
            authors__id__in=interacted_author_ids
        ).distinct()

        title_books = Book.objects.filter(
            title__icontains=similar_titles[0]
        ).distinct() if similar_titles else Book.objects.none()

        recommended_book_ids = (
            set(genre_books.values_list("id", flat=True))
            | set(author_books.values_list("id", flat=True))
            | set(title_books.values_list("id", flat=True))
        ) - interacted_book_ids

        if not recommended_book_ids:
            return self.get_latest_books()

        qs = BookListing.objects.select_related(
            "book", "seller", "seller__profile"
        ).prefetch_related("book__authors", "listing_images")

        qs = qs.filter(
            status=BookListing.Status.AVAILABLE,
            book_id__in=recommended_book_ids,
        )

        qs = qs.annotate(
            favorite_count=Count("wishlisted_by"),
        )

        if self.user.is_authenticated:
            user_fav = Wishlist.objects.filter(
                user=self.user,
                listing=OuterRef("pk"),
            )
            qs = qs.annotate(is_favorited=Exists(user_fav))
        else:
            qs = qs.annotate(
                is_favorited=Value(False, output_field=BooleanField())
            )

        return qs.order_by("-created_at")[:self.page_size]

    def get_genres(self):
        qs = Genre.objects.annotate(
            total_books_count=Count("books"),
        ).order_by("-total_books_count")

        return qs[:10]

    def get_statistics(self):
        active_listings = BookListing.objects.filter(
            status=BookListing.Status.AVAILABLE
        ).count()

        requirements = BookRequirement.objects.filter(
            status=BookRequirement.Status.ACTIVE
        ).count()

        users = User.objects.count()

        return {
            "active_listings": active_listings,
            "requirements": requirements,
            "users": users,
        }

    def calculate_profile_completion(self):
        if not self.user.is_authenticated:
            return 0

        profile = getattr(self.user, "profile", None)
        if profile is None:
            return 0

        score = 0
        total = 5

        if profile.image:
            score += 1

        if profile.college:
            score += 1

        if profile.bio and profile.bio.strip():
            score += 1

        if profile.phone_number and profile.phone_number.strip():
            score += 1

        personalization = profile.personalization_fields or {}
        if personalization.get("user_role"):
            score += 1

        return int((score / total) * 100)

    def build_home_feed(self):
        return {
            "profile_completion": self.calculate_profile_completion(),
            "nearby_books": self.get_nearby_books(),
            "latest_books": self.get_latest_books(),
            "popular_books": self.get_popular_books(),
            "recommended_books": self.get_recommended_books(),
            "featured_books": self.get_featured_books(),
            "genres": self.get_genres(),
            "stats": self.get_statistics(),
        }