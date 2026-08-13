from decimal import Decimal

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from apps.books.models import Book


class BookListing(models.Model):
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
    # Coordinates copy for fast geolocation distance queries (Nearest To You)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    is_boosted = models.BooleanField(default=False, db_index=True)
    views_count = models.PositiveIntegerField(default=0, db_index=True)

    tags = GenericRelation("tags.TaggedItem")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.book.title} - ₹{self.price} by {self.seller.full_name}"


class BookListingImage(models.Model):
    class ImageLabel(models.TextChoices):
        FRONT_COVER = "FRONT_COVER", "Front Cover"
        BACK_COVER = "BACK_COVER", "Back Cover"
        SPINE = "SPINE", "Spine"
        MIDDLE_PAGE = "MIDDLE_PAGE", "Middle Page"
        DAMAGE_1 = "DAMAGE_1", "Damage 1"
        DAMAGE_2 = "DAMAGE_2", "Damage 2"

    book_listing = models.ForeignKey(
        BookListing, on_delete=models.CASCADE, related_name="listing_images"
    )
    image = models.ImageField(upload_to="listing_images/")
    label = models.CharField(
        max_length=20, choices=ImageLabel.choices, default=ImageLabel.FRONT_COVER
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.book_listing} - {self.get_label_display()}"


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
        max_length=20, choices=BookListing.Condition.choices, default=BookListing.Condition.GOOD
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
        BookListing, on_delete=models.CASCADE, related_name="daily_analytics"
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
        BookListing,
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
        "marketplace.BookListing", on_delete=models.CASCADE, related_name="wishlisted_by"
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
        "marketplace.BookListing", on_delete=models.SET_NULL, null=True, blank=True
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


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=PlatformNotification)
def send_push_on_platform_notification(sender, instance, created, **kwargs):
    if created:
        try:
            from apps.notifications.services import _send_expo_push_notifications_async
            # Query user's registered devices (connected via authentication Device model)
            tokens = list(instance.user.devices.values_list("expo_push_token", flat=True))
            if tokens:
                import threading
                extra_data = {
                    "id": instance.id,
                    "notification_type": instance.notification_type,
                    "title": instance.title,
                    "body": instance.body,
                }
                if instance.related_listing:
                    extra_data["related_listing_id"] = instance.related_listing.id
                
                threading.Thread(
                    target=_send_expo_push_notifications_async,
                    args=(tokens, instance.title, instance.body, extra_data),
                    daemon=True
                ).start()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error triggering push notification on PlatformNotification creation: {str(e)}")

@receiver(post_save, sender=Wishlist)
def create_notification_on_wishlist(sender, instance, created, **kwargs):
    if created:
        try:
            PlatformNotification.objects.create(
                user=instance.listing.seller,
                notification_type="BUYER_INTEREST",
                title="New Favorite Alert ❤️",
                body=f"Someone favorited your listing: '{instance.listing.book.title}'.",
                related_listing=instance.listing,
                action_trigger_user=instance.user
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating PlatformNotification on Wishlist create: {str(e)}")

@receiver(post_save, sender=BookContactLedger)
def create_notification_on_contact(sender, instance, created, **kwargs):
    if created:
        try:
            # Try to resolve target seller listing based on exact/contained book title
            from django.db.models import Q
            listing = BookListing.objects.filter(
                Q(book__title__iexact=instance.book_title) | 
                Q(book__title__icontains=instance.book_title)
            ).first()
            
            if listing:
                PlatformNotification.objects.create(
                    user=listing.seller,
                    notification_type="BUYER_INTEREST",
                    title="New Inquiry Received 💬",
                    body=f"A buyer initiated a WhatsApp chat for your listing: '{instance.book_title}'.",
                    related_listing=listing,
                    action_trigger_user=instance.user
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating PlatformNotification on BookContactLedger create: {str(e)}")
