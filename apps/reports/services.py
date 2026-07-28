from django.db import transaction

from apps.marketplace.models import BookListing
from apps.reports.models import Report

# Base queryset with all necessary select_related to avoid N+1 queries
REPORT_QUERYSET = Report.objects.select_related(
    "reporter",
    "reported_user",
    "reported_listing",
    "reported_listing__book",
    "reported_listing__seller",
    "reported_listing__seller__profile",
)


def create_report(*, reporter, report_type, reason, details, reported_user=None, reported_listing=None):
    """
    Create and return a validated Report instance.

    All cross-field validation is handled in the serializer.
    """
    with transaction.atomic():
        report = Report.objects.create(
            reporter=reporter,
            report_type=report_type,
            reason=reason,
            details=details or "",
            reported_user=reported_user,
            reported_listing=reported_listing,
        )
    return report


def get_reports_for_user(*, user):
    """Return queryset of reports submitted by the given user, ordered newest first."""
    return REPORT_QUERYSET.filter(reporter=user).order_by("-created_at")


def get_all_reports():
    """Return queryset of all reports (admin use), ordered newest first."""
    return REPORT_QUERYSET.all().order_by("-created_at")


def update_report_review(*, report, status, review_notes):
    """
    Update a report's status and review notes (admin only).
    Does NOT allow modifying the original report content.
    """
    if status is not None:
        report.status = status
    if review_notes is not None:
        report.review_notes = review_notes
    report.save(update_fields=["status", "review_notes", "updated_at"])
    # Re-fetch with all relations for the response serializer
    fresh_report = REPORT_QUERYSET.get(pk=report.pk)
    return fresh_report

