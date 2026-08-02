from django.urls import path

from apps.reviews.views import (
    ReviewDetailView,
    ReviewListCreateView,
    SellerRatingSummaryView,
    SellerReviewsView,
)

urlpatterns = [
    path("reviews/", ReviewListCreateView.as_view(), name="review-list-create"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path(
        "sellers/<int:seller_id>/reviews/",
        SellerReviewsView.as_view(),
        name="seller-reviews",
    ),
    path(
        "sellers/<int:seller_id>/rating-summary/",
        SellerRatingSummaryView.as_view(),
        name="seller-rating-summary",
    ),
]
