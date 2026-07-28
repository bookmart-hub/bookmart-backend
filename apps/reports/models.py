from django.conf import settings
from django.db import models


class Report(models.Model):
    """User-submitted reports against other users or marketplace listings."""

    class ReportType(models.TextChoices):
        USER = "USER", "Report User"
        LISTING = "LISTING", "Report Listing"

    class ReportStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        RESOLVED = "RESOLVED", "Resolved"
        REJECTED = "REJECTED", "Rejected"

    # ── Listing reasons ──
    LISTING_REASONS = {
        "SCAM",
        "FAKE_LISTING",
        "INAPPROPRIATE",
        "SPAM",
        "WRONG_CATEGORY",
        "OTHER",
    }

    # ── User reasons ──
    USER_REASONS = {
        "HARASSMENT",
        "FAKE_ACCOUNT",
        "SPAM_ACTIVITY",
        "ABUSE",
    }

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_submitted",
        db_index=True,
    )
    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_received",
    )
    reported_listing = models.ForeignKey(
        "marketplace.BookListing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_received",
    )
    reason = models.CharField(max_length=30, db_index=True)
    details = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=15,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )
    review_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def __str__(self):
        target = self.reported_listing_id or self.reported_user_id
        return f"Report #{self.id} ({self.report_type}) by {self.reporter_id} — {self.reason}"

