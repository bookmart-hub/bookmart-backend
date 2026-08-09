from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tags.views import TagViewSet

router = DefaultRouter()
router.register(r"tags", TagViewSet, basename="tags")

urlpatterns = [
    path("", include(router.urls)),
]
