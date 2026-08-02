from django.urls import path

from apps.requirements.views import (
    BookRequirementDetailView,
    BookRequirementListCreateView,
    BookRequirementMyListView,
    BookRequirementNearbyView,
)

urlpatterns = [
    # Public: GET /requirements/  |  Auth: POST /requirements/
    path("requirements/", BookRequirementListCreateView.as_view(), name="requirement-list-create"),
    # Auth: GET /requirements/me/
    path("requirements/me/", BookRequirementMyListView.as_view(), name="requirement-my-list"),
    # Auth: GET /requirements/nearby/
    path("requirements/nearby/", BookRequirementNearbyView.as_view(), name="requirement-nearby"),
    # Anyone: GET /requirements/{id}/  |  Owner: PATCH/DELETE /requirements/{id}/
    path("requirements/<int:pk>/", BookRequirementDetailView.as_view(), name="requirement-detail"),
]
