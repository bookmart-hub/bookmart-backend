from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.core.views.college import CollegeViewSet
from apps.core.views.profile import ProfileOnboardingView, ProfileViewSet

router = DefaultRouter()
router.register("colleges", CollegeViewSet)
router.register("profile", ProfileViewSet, "profile")

urlpatterns = [
    path(
        "profile/onboarding", ProfileOnboardingView.as_view(), name="profile-onboarding"
    ),
] + router.urls
