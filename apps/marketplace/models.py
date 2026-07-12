from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.books.models import Book


class Listing(models.Model):
    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        LIKE_NEW = "LIKE_NEW", "Like New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"  # Aligned with 18-list-book.png
        POOR = "POOR", "Poor"  # Aligned with 18-list-book.png

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        PENDING = "PENDING", "Pending"
        SOLD = "SOLD", "Sold"

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="listings")
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(
        max_length=20, choices=Condition.choices, default=Condition.GOOD
    )
    condition_notes = models.TextField(
        blank=True, help_text="Specific tattered page details"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True
    )
    images = models.JSONField(
        default=list, help_text="Array of cloud storage photo URLs"
    )

    # Coordinates copy for fast geolocation distance queries (Nearest To You)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.book.title} - ₹{self.price} by {self.seller.username}"


class BookRequirement(models.Model):
    """Demand Side: Replaces original BookRequest to map precisely to 17-post-book-requirement.png"""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        FULFILLED = "FULFILLED", "Fulfilled"
        CLOSED = "CLOSED", "Closed"

    book = models.ForeignKey(
        Book, on_delete=models.PROTECT, related_name="requirements"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requirements"
    )

    # Price range mapping matching UI form fields
    min_budget = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal(0.0)
    )
    max_budget = models.DecimalField(max_digits=10, decimal_places=2)

    condition_preferred = models.CharField(
        max_length=20, choices=Listing.Condition.choices, default=Listing.Condition.GOOD
    )
    additional_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Req: {self.book.title} Max Budget: ₹{self.max_budget}"


class ListingAnalyticsDaily(models.Model):
    """
    Aggregated timeseries stats backing screen 19-seller-analytics.jpg.
    Tracks structural interactions per listing per day.
    """

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="daily_analytics"
    )
    date = models.DateField(db_index=True)

    views_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)
    wa_contacts_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("listing", "date")
        verbose_name_plural = "Listing Analytics (Daily)"


class PlatformReport(models.Model):
    """Trust & Safety mapping for screen 20-report-user-book.png"""

    class ReportType(models.TextChoices):
        LISTING = "LISTING", "Report Listing"
        USER = "USER", "Report User"

    class ReasonCategory(models.TextChoices):
        SCAM_FRAUD = "SCAM_FRAUD", "Scam / Fraud"
        FAKE_LISTING = "FAKE_LISTING", "Fake Listing"
        INAPPROPRIATE = "INAPPROPRIATE", "Inappropriate Content"
        SPAM = "SPAM", "Spam"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
    )
    report_type = models.CharField(max_length=15, choices=ReportType.choices)

    # Generic relations replacement via lightweight semantic tracking IDs
    target_listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="targeted_reports",
    )

    category = models.CharField(max_length=30, choices=ReasonCategory.choices)
    details = models.TextField(
        help_text="User descriptive notes collected during step 3"
    )

    is_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter.username} - Type: {self.report_type} ({self.category})"


class Wishlist(models.Model):
    """Backs screen 22-wishlist.png"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    listing = models.ForeignKey(
        "marketplace.Listing", on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "listing")


class PlatformNotification(models.Model):
    """Backs screen 23-notification.png"""

    class NotificationType(models.TextChoices):
        PRICE_DROP = "PRICE_DROP", "Price Drop Alert"
        BUYER_INTEREST = "BUYER_INTEREST", "Interested Buyer"
        NEW_LISTING = "NEW_LISTING", "New Book Alert"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices
    )
    title = models.CharField(max_length=255)
    body = models.TextField()

    # Context references
    related_listing = models.ForeignKey(
        "marketplace.Listing", on_delete=models.SET_NULL, null=True, blank=True
    )
    action_trigger_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BookContactLedger(models.Model):
    """Backs screen 24-book-contacts.png transaction list"""

    class DealRole(models.TextChoices):
        BOUGHT = "BOUGHT", "Bought"
        SOLD = "SOLD", "Sold"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deal_logs"
    )
    contact_person_name = models.CharField(max_length=255)
    book_title = models.CharField(max_length=255)
    deal_type = models.CharField(max_length=10, choices=DealRole.choices)
    price_recorded = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date"]
