from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.marketplace.models import BookListing
from apps.reports.models import Report

User = get_user_model()


class UserNestedSerializer(serializers.ModelSerializer):
    """Lightweight user representation for report responses with profile image."""

    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "profile_image"]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_profile_image(self, obj):
        if hasattr(obj, "profile") and obj.profile.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.profile.image.url)
            return obj.profile.image.url
        return None


class BookNestedMinSerializer(serializers.ModelSerializer):
    """Minimal book representation for report listing target."""

    class Meta:
        model = BookListing.book.field.related_model
        fields = ["id", "title", "cover_url"]


class ListingBriefSerializer(serializers.ModelSerializer):
    """Enriched listing representation for moderators reviewing reports."""

    book = BookNestedMinSerializer(read_only=True)
    seller = UserNestedSerializer(read_only=True)

    class Meta:
        model = BookListing
        fields = [
            "id",
            "book",
            "seller",
            "price",
            "status",
            "created_at",
        ]


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new report (POST /reports/)."""

    class Meta:
        model = Report
        fields = [
            "report_type",
            "reported_user",
            "reported_listing",
            "reason",
            "details",
        ]

    def validate_report_type(self, value):
        if value not in Report.ReportType.values:
            raise serializers.ValidationError(
                f"Invalid report_type. Must be one of: {', '.join(Report.ReportType.values)}."
            )
        return value

    def validate_reason(self, value):
        report_type = self.initial_data.get("report_type")
        if report_type == Report.ReportType.LISTING:
            allowed = Report.LISTING_REASONS
        elif report_type == Report.ReportType.USER:
            allowed = Report.USER_REASONS
        else:
            allowed = set()

        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid reason for report_type '{report_type}'. "
                f"Allowed reasons: {', '.join(sorted(allowed))}."
            )
        return value

    def validate(self, attrs):
        report_type = attrs.get("report_type")
        reported_user = attrs.get("reported_user")
        reported_listing = attrs.get("reported_listing")
        reporter = self.context["request"].user

        # ── Exactly one target must be set ──
        has_user = reported_user is not None
        has_listing = reported_listing is not None

        if report_type == Report.ReportType.USER and not has_user:
            raise serializers.ValidationError(
                {"reported_user": "reported_user is required for report_type='USER'."}
            )
        if report_type == Report.ReportType.LISTING and not has_listing:
            raise serializers.ValidationError(
                {
                    "reported_listing": "reported_listing is required for report_type='LISTING'."
                }
            )

        if has_user and has_listing:
            raise serializers.ValidationError(
                "You cannot set both reported_user and reported_listing. Choose one."
            )
        if not has_user and not has_listing:
            raise serializers.ValidationError(
                "Either reported_user or reported_listing must be provided."
            )

        # ── Cannot report yourself ──
        if has_user and reported_user == reporter:
            raise serializers.ValidationError(
                {"reported_user": "You cannot report yourself."}
            )

        # ── Cannot report your own listing ──
        if has_listing:
            if reported_listing.seller == reporter:
                raise serializers.ValidationError(
                    {
                        "reported_listing": "You cannot report your own listing."
                    }
                )

        # ── Duplicate report check ──
        active_statuses = [Report.ReportStatus.PENDING, Report.ReportStatus.UNDER_REVIEW]
        if has_user:
            duplicate = Report.objects.filter(
                reporter=reporter,
                reported_user=reported_user,
                status__in=active_statuses,
            ).exists()
            if duplicate:
                raise serializers.ValidationError(
                    {
                        "reported_user": "You have already reported this user. "
                        "Your previous report is still pending or under review."
                    }
                )
        if has_listing:
            duplicate = Report.objects.filter(
                reporter=reporter,
                reported_listing=reported_listing,
                status__in=active_statuses,
            ).exists()
            if duplicate:
                raise serializers.ValidationError(
                    {
                        "reported_listing": "You have already reported this listing. "
                        "Your previous report is still pending or under review."
                    }
                )

        return attrs


class ReportResponseSerializer(serializers.ModelSerializer):
    """Serializer for reading report data with full nested details."""

    reporter = UserNestedSerializer(read_only=True)
    reported_user = UserNestedSerializer(read_only=True)
    reported_listing = ListingBriefSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "report_type",
            "reported_user",
            "reported_listing",
            "reason",
            "details",
            "status",
            "review_notes",
            "created_at",
            "updated_at",
        ]


class ReportAdminUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin review of a report (PATCH /reports/{id}/).
    Only status and review_notes can be updated.
    """

    class Meta:
        model = Report
        fields = ["status", "review_notes"]

    def validate_status(self, value):
        if value not in Report.ReportStatus.values:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(Report.ReportStatus.values)}."
            )
        return value

