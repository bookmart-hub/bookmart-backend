from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.home_feed.views import HomeFeedViewSet

router = DefaultRouter()
router.register("home", HomeFeedViewSet, basename="home-feed")

urlpatterns = [
    path("", include(router.urls)),
]