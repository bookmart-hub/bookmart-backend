from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, mixins, permissions, viewsets

from apps.core.models import College
from apps.core.serializers import CollegeSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Retrieve colleges list",
        description="Fetches all the college details.",
        tags=["College Management"],
    ),
    retrieve=extend_schema(
        summary="Retrieve college details",
        description="Fetches the details of the specified college.",
        tags=["College Management"],
    ),
    create=extend_schema(
        summary="Add a new college",
        description="Creates a new college record with the provided details.",
        tags=["College Management"],
    ),
)
class CollegeViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = College.objects.all()
    serializer_class = CollegeSerializer
    permission_classes = [permissions.IsAuthenticated]

    search_fields = ["name", "district", "state"]
    ordering_fields = ["name", "district", "state"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
