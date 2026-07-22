from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.core.views.college import CollegeViewSet
from apps.core.views.profile import ProfileOnboardingView, ProfileViewSet
from apps.core.views.health import HealthCheckView

router = DefaultRouter()
router.register("colleges", CollegeViewSet)
router.register("profile", ProfileViewSet, "profile")

urlpatterns = [
    path("health", HealthCheckView.as_view(), name="health-check"),
    path(
        "profile/onboarding", ProfileOnboardingView.as_view(), name="profile-onboarding"
    ),
] + router.urls
