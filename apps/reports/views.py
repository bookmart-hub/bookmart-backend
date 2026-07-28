from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.reports.models import Report
from apps.reports.pagination import ReportsPagination
from apps.reports.serializers import (
    ReportAdminUpdateSerializer,
    ReportCreateSerializer,
    ReportResponseSerializer,
)
from apps.reports.services import (
    create_report,
    get_all_reports,
    get_reports_for_user,
    update_report_review,
)


@extend_schema_view(
    post=extend_schema(
        summary="Submit a report",
        description=(
            "Report another user or a marketplace listing. A user cannot report themselves, "
            "cannot report their own listing, and cannot submit a duplicate report while the "
            "previous one is still PENDING or UNDER_REVIEW."
        ),
        request=ReportCreateSerializer,
        responses={
            201: ReportResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Report a listing",
                summary="Report a marketplace listing as SCAM",
                value={
                    "report_type": "LISTING",
                    "reported_listing": 15,
                    "reason": "SCAM",
                    "details": "Seller asked me to pay outside Bookmart.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Report a user",
                summary="Report a user for harassment",
                value={
                    "report_type": "USER",
                    "reported_user": 8,
                    "reason": "HARASSMENT",
                    "details": "Sending abusive messages.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Report created response",
                summary="Successful report creation",
                value={
                    "id": 1,
                    "reporter": {
                        "id": 1,
                        "full_name": "John Doe",
                        "email": "john@example.com",
                        "profile_image": None,
                    },
                    "report_type": "LISTING",
                    "reported_user": None,
                    "reported_listing": {
                        "id": 15,
                        "book": {
                            "id": 10,
                            "title": "Example Book",
                            "cover_url": "https://covers.openlibrary.org/b/id/123-L.jpg",
                        },
                        "seller": {
                            "id": 5,
                            "full_name": "Jane Seller",
                            "email": "jane@example.com",
                            "profile_image": None,
                        },
                        "price": "250.00",
                        "status": "AVAILABLE",
                        "created_at": "2024-01-15T10:30:00Z",
                    },
                    "reason": "SCAM",
                    "details": "Seller asked me to pay outside Bookmart.",
                    "status": "PENDING",
                    "review_notes": "",
                    "created_at": "2024-03-01T12:00:00Z",
                    "updated_at": "2024-03-01T12:00:00Z",
                },
                response_only=True,
            ),
        ],
        tags=["Reports"],
    ),
    get=extend_schema(
        summary="List all reports (admin)",
        description=(
            "Returns a paginated list of all reports in the system, ordered newest first. "
            "Supports filtering by status, report_type, reason, and date range, "
            "as well as search by reporter name/email, reported user name, or book title."
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
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f"Filter by status: {', '.join(Report.ReportStatus.values)}.",
            ),
            OpenApiParameter(
                name="report_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f"Filter by type: {', '.join(Report.ReportType.values)}.",
            ),
            OpenApiParameter(
                name="reason",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by reason code.",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Search across reporter name, reporter email, "
                    "reported user name, and book title (if reporting a listing)."
                ),
            ),
            OpenApiParameter(
                name="created_at_after",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter reports created on or after this date (ISO 8601).",
            ),
            OpenApiParameter(
                name="created_at_before",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter reports created on or before this date (ISO 8601).",
            ),
        ],
        responses={200: ReportResponseSerializer(many=True)},
        tags=["Reports - Admin"],
    ),
)
class ReportListView(generics.GenericAPIView):
    """
    GET  /api/v1/reports/   — Admin: list all reports (paginated, filterable, searchable)
    POST /api/v1/reports/   — User:  submit a new report
    """

    queryset = Report.objects.all()
    pagination_class = ReportsPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReportCreateSerializer
        return ReportResponseSerializer

    # ── POST: User creates a report ──
    def post(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        report = create_report(
            reporter=request.user,
            report_type=serializer.validated_data["report_type"],
            reason=serializer.validated_data["reason"],
            details=serializer.validated_data.get("details", ""),
            reported_user=serializer.validated_data.get("reported_user"),
            reported_listing=serializer.validated_data.get("reported_listing"),
        )
        response_serializer = ReportResponseSerializer(
            report, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── GET: Admin lists all reports (paginated) ──
    def get(self, request, *args, **kwargs):
        qs = get_all_reports()

        # ── Apply filters ──
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        report_type_param = request.query_params.get("report_type")
        if report_type_param:
            qs = qs.filter(report_type=report_type_param)

        reason_param = request.query_params.get("reason")
        if reason_param:
            qs = qs.filter(reason=reason_param)

        created_at_after = request.query_params.get("created_at_after")
        if created_at_after:
            qs = qs.filter(created_at__gte=created_at_after)

        created_at_before = request.query_params.get("created_at_before")
        if created_at_before:
            qs = qs.filter(created_at__lte=created_at_before)

        # ── Apply search ──
        search_param = request.query_params.get("search")
        if search_param:
            qs = qs.filter(
                Q(reporter__full_name__icontains=search_param)
                | Q(reporter__email__icontains=search_param)
                | Q(reported_user__full_name__icontains=search_param)
                | Q(reported_user__email__icontains=search_param)
                | Q(reported_listing__book__title__icontains=search_param)
            )

        # ── Paginate ──
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ReportResponseSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        # Fallback (unpaginated)
        serializer = ReportResponseSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        summary="List my reports",
        description=(
            "Returns a paginated list of reports submitted by the currently authenticated user, "
            "ordered by most recent first."
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
        responses={200: ReportResponseSerializer(many=True)},
        tags=["Reports"],
    ),
)
class ReportMyListView(generics.ListAPIView):
    """GET /api/v1/reports/me/ — Current user's reports (paginated)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportResponseSerializer
    pagination_class = ReportsPagination

    def get_queryset(self):
        return get_reports_for_user(user=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve report detail (admin)",
        description="Fetch a single report by ID, including full reporter, target user, and target listing details.",
        responses={
            200: ReportResponseSerializer,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Reports - Admin"],
    ),
    patch=extend_schema(
        summary="Update report review (admin)",
        description=(
            "Update the status and/or review notes of a report. "
            "Only `status` and `review_notes` can be modified. "
            "The following fields are immutable: reporter, report_type, reported_user, "
            "reported_listing, reason, details, created_at."
        ),
        request=ReportAdminUpdateSerializer,
        responses={
            200: ReportResponseSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Review report",
                summary="Mark a report as RESOLVED",
                value={
                    "status": "RESOLVED",
                    "review_notes": "Investigated. No violation found. Report resolved.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Review report response",
                summary="Updated report response",
                value={
                    "id": 1,
                    "reporter": {
                        "id": 1,
                        "full_name": "John Doe",
                        "email": "john@example.com",
                        "profile_image": None,
                    },
                    "report_type": "LISTING",
                    "reported_user": None,
                    "reported_listing": {
                        "id": 15,
                        "book": {
                            "id": 10,
                            "title": "Example Book",
                            "cover_url": "https://covers.openlibrary.org/b/id/123-L.jpg",
                        },
                        "seller": {
                            "id": 5,
                            "full_name": "Jane Seller",
                            "email": "jane@example.com",
                            "profile_image": None,
                        },
                        "price": "250.00",
                        "status": "AVAILABLE",
                        "created_at": "2024-01-15T10:30:00Z",
                    },
                    "reason": "SCAM",
                    "details": "Seller asked me to pay outside Bookmart.",
                    "status": "RESOLVED",
                    "review_notes": "Investigated. No violation found. Report resolved.",
                    "created_at": "2024-03-01T12:00:00Z",
                    "updated_at": "2024-03-02T09:00:00Z",
                },
                response_only=True,
            ),
        ],
        tags=["Reports - Admin"],
    ),
)
class ReportDetailView(generics.GenericAPIView):
    """
    GET   /api/v1/reports/{id}/  — Admin: get full report detail
    PATCH /api/v1/reports/{id}/  — Admin: update status & review_notes only
    """

    permission_classes = [permissions.IsAdminUser]
    queryset = Report.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ReportAdminUpdateSerializer
        return ReportResponseSerializer

    def get_object(self):
        from apps.reports.services import REPORT_QUERYSET
        return generics.get_object_or_404(
            REPORT_QUERYSET, pk=self.kwargs["pk"]
        )

    # ── GET: Admin retrieves report detail ──
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ReportResponseSerializer(
            instance, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── PATCH: Admin updates status/review_notes ──
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ReportAdminUpdateSerializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        report = update_report_review(
            report=instance,
            status=serializer.validated_data.get("status"),
            review_notes=serializer.validated_data.get("review_notes"),
        )
        response_serializer = ReportResponseSerializer(
            report, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

