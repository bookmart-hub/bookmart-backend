from django.urls import path

from apps.favorites.views import (
    FavoriteAdminView,
    FavoriteCheckView,
    FavoriteCountView,
    FavoriteDeleteView,
    FavoriteListCreateView,
)

urlpatterns = [
    path("favorites/", FavoriteListCreateView.as_view(), name="favorite-list-create"),
    path("favorites/check/<int:listing_id>/", FavoriteCheckView.as_view(), name="favorite-check"),
    path("favorites/count/<int:listing_id>/", FavoriteCountView.as_view(), name="favorite-count"),
    path("favorites/<int:listing_id>/", FavoriteDeleteView.as_view(), name="favorite-delete"),
    path("favorites/admin/", FavoriteAdminView.as_view(), name="favorite-admin"),
]
