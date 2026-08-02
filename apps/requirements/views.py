from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response

from apps.requirements.filters import BookRequirementFilter
from apps.requirements.models import BookRequirement
from apps.requirements.pagination import RequirementsPagination
from apps.requirements.serializers import (
    BookRequirementCreateSerializer,
    BookRequirementListSerializer,
    BookRequirementNearbySerializer,
    BookRequirementUpdateSerializer,
)
from apps.requirements.services import (
    create_requirement,
    get_active_requirements,
    get_nearby_requirements,
    get_requirement_by_id,
    get_requirements_for_user,
    update_requirement,
)

DEFAULT_RADIUS_KM = 10.0
MAX_RADIUS_KM = 100.0


@extend_schema_view(
    post=extend_schema(
        summary="Create a book requirement",
        description=(
            "Submit a new 'Wanted Book' requirement. Only authenticated users can create requirements. "
            "You can create multiple requirements."
        ),
        request=BookRequirementCreateSerializer,
        responses={
            201: BookRequirementListSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Create requirement",
                summary="Post a wanted book requirement",
                value={
                    "book_title": "Operating System Concepts",
                    "preferred_condition": "GOOD",
                    "min_price": "300.00",
                    "max_price": "450.00",
                    "notes": "Need 10th edition if possible.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create requirement response",
                summary="Successful requirement creation",
                value={
                    "id": 12,
                    "user": {
                        "id": 5,
                        "full_name": "Amit Roy",
                        "profile_image": None,
                    },
                    "book_title": "Operating System Concepts",
                    "preferred_condition": "GOOD",
                    "min_price": "300.00",
                    "max_price": "450.00",
                    "notes": "Need 10th edition if possible.",
                    "status": "ACTIVE",
                    "created_at": "2025-01-15T10:30:00Z",
                    "updated_at": "2025-01-15T10:30:00Z",
                },
                response_only=True,
            ),
        ],
        tags=["Book Requirements"],
    ),
    get=extend_schema(
        summary="List active book requirements",
        description=(
            "Returns a paginated list of all ACTIVE book requirements. "
            "Supports searching by book title, filtering by condition, price range, "
            "and ordering by created_at or -created_at."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page number for paginated results.",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Number of results per page (max 100).",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search by book title (case-insensitive partial match).",
            ),
            OpenApiParameter(
                name="condition",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f"Filter by preferred condition: {', '.join(BookRequirement.Condition.values)}.",
            ),
            OpenApiParameter(
                name="min_price",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by minimum price (inclusive).",
            ),
            OpenApiParameter(
                name="max_price",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by maximum price (inclusive).",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Order results. Options:\n"
                    "  - `created_at` (oldest first)\n"
                    "  - `-created_at` (newest first, default)"
                ),
            ),
        ],
        responses={200: BookRequirementListSerializer(many=True)},
        tags=["Book Requirements"],
    ),
)
class BookRequirementListCreateView(generics.GenericAPIView):
    """
    GET  /api/v1/requirements/   — Public: list ACTIVE requirements (paginated)
    POST /api/v1/requirements/   — Auth: create a new requirement
    """

    queryset = BookRequirement.objects.all()
    pagination_class = RequirementsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookRequirementFilter
    search_fields = ["book_title"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookRequirementCreateSerializer
        return BookRequirementListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        if self.request.method == "GET":
            return get_active_requirements()
        return BookRequirement.objects.all()

    # ── POST: Create requirement ──
    def post(self, request, *args, **kwargs):
        serializer = BookRequirementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        requirement = create_requirement(
            user=request.user,
            book=validated.get("book"),
            book_title=validated["book_title"],
            preferred_condition=validated.get("preferred_condition", BookRequirement.Condition.GOOD),
            min_price=validated.get("min_price"),
            max_price=validated.get("max_price"),
            notes=validated.get("notes", ""),
            latitude=validated.get("latitude"),
            longitude=validated.get("longitude"),
        )

        response_serializer = BookRequirementListSerializer(
            requirement, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── GET: List active requirements (public) ──
    def get(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = BookRequirementListSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = BookRequirementListSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve requirement details",
        description="Fetch full details of a single book requirement by ID.",
        responses={
            200: BookRequirementListSerializer,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Book Requirements"],
    ),
    patch=extend_schema(
        summary="Update a book requirement (owner only)",
        description=(
            "Partially update your own book requirement. Only the owner can update. "
            "You can update: book_title, preferred_condition, min_price, max_price, notes, and status."
        ),
        request=BookRequirementUpdateSerializer,
        responses={
            200: BookRequirementListSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Update requirement",
                summary="Mark requirement as fulfilled",
                value={
                    "status": "FULFILLED",
                    "notes": "Found a copy!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update requirement error",
                summary="Permission denied for non-owner",
                value={"detail": "You do not have permission to modify this requirement."},
                response_only=True,
            ),
        ],
        tags=["Book Requirements"],
    ),
    delete=extend_schema(
        summary="Delete a book requirement (owner only)",
        description="Permanently delete your own book requirement. Only the owner can delete.",
        responses={
            204: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Book Requirements"],
    ),
)
class BookRequirementDetailView(generics.GenericAPIView):
    """
    GET    /api/v1/requirements/{id}/  — Anyone: get requirement detail
    PATCH  /api/v1/requirements/{id}/  — Owner: update requirement
    DELETE /api/v1/requirements/{id}/  — Owner: delete requirement
    """

    queryset = BookRequirement.objects.select_related("user", "user__profile")

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return BookRequirementUpdateSerializer
        return BookRequirementListSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        return generics.get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def _check_owner(self, requirement, user):
        """Check if the user is the owner of the requirement (or admin)."""
        if not user.is_staff and requirement.user != user:
            return Response(
                {"detail": "You do not have permission to modify this requirement."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    # ── GET: Anyone ──
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = BookRequirementListSerializer(
            instance, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── PATCH: Owner or admin ──
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        error = self._check_owner(instance, request.user)
        if error:
            return error

        serializer = BookRequirementUpdateSerializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        update_data = dict(serializer.validated_data)
        requirement = update_requirement(requirement=instance, data=update_data)

        response_serializer = BookRequirementListSerializer(
            requirement, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    # ── DELETE: Owner or admin ──
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        error = self._check_owner(instance, request.user)
        if error:
            return error

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(
        summary="List my book requirements",
        description=(
            "Returns a paginated list of book requirements belonging to the currently "
            "authenticated user, ordered by most recent first."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page number for paginated results.",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Number of results per page (max 100).",
            ),
        ],
        responses={200: BookRequirementListSerializer(many=True)},
        tags=["Book Requirements"],
    ),
)
class BookRequirementMyListView(generics.ListAPIView):
    """GET /api/v1/requirements/me/ — Current user's requirements (paginated)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookRequirementListSerializer
    pagination_class = RequirementsPagination

    def get_queryset(self):
        return get_requirements_for_user(user=self.request.user)


@extend_schema(
    summary="Find nearby book requirements",
    description=(
        "Returns a paginated list of ACTIVE book requirements within a radius "
        "of the given coordinates, ordered by distance by default. "
        "Supports search, condition, and price filters. "
        "Authenticated users only."
    ),
    parameters=[
        OpenApiParameter(
            name="lat",
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Center latitude in degrees.",
        ),
        OpenApiParameter(
            name="lng",
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Center longitude in degrees.",
        ),
        OpenApiParameter(
            name="radius",
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            required=False,
            description=f"Search radius in kilometers (default {DEFAULT_RADIUS_KM}, max {MAX_RADIUS_KM}).",
        ),
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Search by book title.",
        ),
        OpenApiParameter(
            name="condition",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=f"Filter by preferred condition: {', '.join(BookRequirement.Condition.values)}.",
        ),
        OpenApiParameter(
            name="min_price",
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by minimum price (inclusive).",
        ),
        OpenApiParameter(
            name="max_price",
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filter by maximum price (inclusive).",
        ),
        OpenApiParameter(
            name="ordering",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Order results. Options:\n"
                "  - `distance` (nearest first, default)\n"
                "  - `-distance` (farthest first)\n"
                "  - `created_at` (oldest first)\n"
                "  - `-created_at` (newest first)"
            ),
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number for paginated results.",
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Number of results per page (max 100).",
        ),
    ],
    responses={
        200: BookRequirementNearbySerializer(many=True),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    tags=["Book Requirements"],
)
class BookRequirementNearbyView(generics.GenericAPIView):
    """
    GET /api/v1/requirements/nearby/ — Auth: nearby requirements with distance
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookRequirementNearbySerializer
    pagination_class = RequirementsPagination
    filter_backends = []

    def get(self, request, *args, **kwargs):
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius = request.query_params.get("radius", DEFAULT_RADIUS_KM)
        search = request.query_params.get("search")
        condition = request.query_params.get("condition")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        ordering = request.query_params.get("ordering", "distance")

        if lat is None or lng is None:
            return Response(
                {"detail": "lat and lng are required query parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return Response(
                {"detail": "lat and lng must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not -90 <= lat <= 90:
            return Response(
                {"detail": "lat must be between -90 and 90."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not -180 <= lng <= 180:
            return Response(
                {"detail": "lng must be between -180 and 180."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            radius = float(radius)
            if radius <= 0 or radius > MAX_RADIUS_KM:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"detail": f"radius must be a positive number up to {MAX_RADIUS_KM} km."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = get_nearby_requirements(
            center_lat=lat,
            center_lng=lng,
            radius_km=radius,
            search=search,
            condition=condition,
            min_price=min_price,
            max_price=max_price,
            ordering=ordering,
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = BookRequirementNearbySerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = BookRequirementNearbySerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
