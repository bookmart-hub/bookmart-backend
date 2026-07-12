from http import HTTPStatus

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, mixins, permissions, views, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.models import Profile
from apps.core.serializers import ProfileOnboardingSerializer, ProfileResponseSerializer


@extend_schema_view(
    retrieve=extend_schema(
        summary="Retrieve user profile",
        description="Fetches the profile details of the currently authenticated user.",
        tags=["Profile Management"],
    ),
    update=extend_schema(
        summary="Update user profile",
        description="Updates the profile details of the currently authenticated user.",
        tags=["Profile Management"],
    ),
)
class ProfileViewSet(
    viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin
):
    queryset = Profile.objects.all()
    serializer_class = ProfileResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    search_fields = ["college__name", "city_location", "user__full_name"]
    ordering_fields = ["college__name", "city_location", "user__full_name"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]


class ProfileOnboardingView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileOnboardingSerializer

    @extend_schema(
        summary="User Onboarding",
        description="Fetches the onboarding data from the user and stores in profile.",
        tags=["Profile Management"],
    )
    def post(self, request: Request):
        serializer = ProfileOnboardingSerializer(
            request.user.profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        return Response(
            data={"profile": ProfileResponseSerializer(profile).data},
            status=HTTPStatus.CREATED,
        )
