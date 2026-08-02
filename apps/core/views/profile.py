from http import HTTPStatus

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import decorators, filters, mixins, permissions, views, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.models import Profile
from apps.core.serializers import (
    ProfileOnboardingSerializer,
    ProfileResponseSerializer,
    ProfileUpdateSerializer,
)


class ProfileViewSet(
    viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin
):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    search_fields = ["college__name", "city_location", "user__full_name"]
    ordering_fields = ["college__name", "city_location", "user__full_name"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_object(self):
        if self.action == "retrieve":
            return super().get_object()
        return self.request.user.profile

    def get_queryset(self):
        if self.action == "retrieve":
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return ProfileUpdateSerializer
        return ProfileResponseSerializer

    @extend_schema(
        methods=["GET"],
        summary="Retrieve user profile",
        description="Fetches the profile details of the currently authenticated user.",
        tags=["Profile Management"],
        responses=ProfileResponseSerializer,
    )
    @extend_schema(
        methods=["PATCH"],
        summary="Partially update user profile",
        description="Update one or more fields of the authenticated user's profile.",
        tags=["Profile Management"],
        request=ProfileUpdateSerializer,
        responses=ProfileResponseSerializer,
    )
    @decorators.action(
        detail=False,
        methods=["GET", "PATCH"],
        url_path="me",
    )
    def me(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        if request.method.upper() == "PATCH":
            serializer = ProfileUpdateSerializer(
                instance=profile,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            profile.refresh_from_db()

        serializer = ProfileResponseSerializer(profile, context={"request": request})
        return Response(serializer.data)


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
