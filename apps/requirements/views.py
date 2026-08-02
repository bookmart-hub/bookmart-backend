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
    BookRequirementUpdateSerializer,
)
from apps.requirements.services import (
    create_requirement,
    get_active_requirements,
    get_requirement_by_id,
    get_requirements_for_user,
    update_requirement,
)


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

        requirement = create_requirement(
            user=request.user,
            book_title=serializer.validated_data["book_title"],
            preferred_condition=serializer.validated_data.get("preferred_condition", BookRequirement.Condition.GOOD),
            min_price=serializer.validated_data.get("min_price"),
            max_price=serializer.validated_data.get("max_price"),
            notes=serializer.validated_data.get("notes", ""),
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

        # Only pass fields that were actually provided
        update_data = {}
        for field in serializer.validated_data:
            if field in request.data:
                update_data[field] = serializer.validated_data[field]

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
