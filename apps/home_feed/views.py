from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.home_feed.services import HomeFeedService
from apps.home_feed.serializers import HomeFeedSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Home Feed",
        description=(
            "Returns the complete home feed data for the authenticated user, "
            "including nearby books, latest listings, popular listings, recommended "
            "listings, featured books, genres, platform statistics, and profile "
            "completion score. All sections are returned in a single response to "
            "minimize the number of API calls the mobile client needs to make."
        ),
        parameters=[
            OpenApiParameter(
                name="lat",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Latitude for nearby books filtering.",
            ),
            OpenApiParameter(
                name="lng",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Longitude for nearby books filtering.",
            ),
            OpenApiParameter(
                name="radius",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search radius in kilometres for nearby books (default 10, max 100).",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Number of listings per section (max 15).",
            ),
        ],
        responses={
            200: HomeFeedSerializer,
            401: OpenApiTypes.OBJECT,
        },
        tags=["Home Feed"],
    ),
)
class HomeFeedViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        lat_raw = request.query_params.get("lat")
        lng_raw = request.query_params.get("lng")
        radius_raw = request.query_params.get("radius")
        page_size_raw = request.query_params.get("page_size")

        lat = None
        lng = None
        radius = 10.0
        page_size = 10

        if lat_raw is not None:
            try:
                lat = float(lat_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "'lat' must be a valid floating-point number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if lng_raw is not None:
            try:
                lng = float(lng_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "'lng' must be a valid floating-point number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if radius_raw is not None:
            try:
                radius = float(radius_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "'radius' must be a valid floating-point number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if page_size_raw is not None:
            try:
                page_size = int(page_size_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "'page_size' must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if page_size < 1:
            page_size = 1

        service = HomeFeedService(
            user=request.user,
            lat=lat,
            lng=lng,
            radius=radius,
            page_size=page_size,
        )

        feed_data = service.build_home_feed()

        serializer = HomeFeedSerializer(
            feed_data,
            context={"request": request},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)