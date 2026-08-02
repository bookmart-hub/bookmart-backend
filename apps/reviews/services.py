from django.db.models import Count, Avg, Q
from django.db.models.functions import Cast
from django.db.models import IntegerField

from apps.authentication.models import User
from apps.marketplace.models import BookListing
from apps.reviews.models import Review


def create_review(reviewer: User, listing: BookListing, rating: int, review_text: str = "") -> Review:
    if listing.seller == reviewer:
        raise ValueError("You cannot review your own listing.")

    if Review.objects.filter(reviewer=reviewer, listing=listing).exists():
        raise ValueError("You have already reviewed this listing.")

    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5.")

    return Review.objects.create(
        reviewer=reviewer,
        seller=listing.seller,
        listing=listing,
        rating=rating,
        review=review_text,
    )


def update_review(review: Review, user: User, rating: int, review_text: str = "") -> Review:
    if review.reviewer != user:
        raise ValueError("You do not have permission to modify this review.")

    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5.")

    review.rating = rating
    review.review = review_text
    review.save()
    return review


def delete_review(review: Review, user: User) -> bool:
    if review.reviewer != user:
        raise ValueError("You do not have permission to delete this review.")
    review.delete()
    return True


def seller_rating_summary(seller: User) -> dict:
    reviews = Review.objects.filter(seller=seller)
    count = reviews.count()
    if count == 0:
        return {
            "average_rating": 0.0,
            "rating_count": 0,
            "rating_distribution": {
                "5": 0,
                "4": 0,
                "3": 0,
                "2": 0,
                "1": 0,
            },
        }

    distribution = {
        str(i): reviews.filter(rating=i).count()
        for i in range(1, 6)
    }

    return {
        "average_rating": round(reviews.aggregate(avg=Avg("rating"))["avg"] or 0.0, 1),
        "rating_count": count,
        "rating_distribution": distribution,
    }


def get_seller_reviews(seller: User):
    return Review.objects.filter(seller=seller).select_related(
        "reviewer", "seller", "listing", "listing__book"
    ).prefetch_related("listing__listing_images")
