from django.urls import path

from apps.requirements.views import (
    BookRequirementDetailView,
    BookRequirementListCreateView,
    BookRequirementMyListView,
)

urlpatterns = [
    # Public: GET /requirements/  |  Auth: POST /requirements/
    path("requirements/", BookRequirementListCreateView.as_view(), name="requirement-list-create"),
    # Auth: GET /requirements/me/
    path("requirements/me/", BookRequirementMyListView.as_view(), name="requirement-my-list"),
    # Anyone: GET /requirements/{id}/  |  Owner: PATCH/DELETE /requirements/{id}/
    path("requirements/<int:pk>/", BookRequirementDetailView.as_view(), name="requirement-detail"),
]
