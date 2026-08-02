from django.conf import settings
from django.db import models


class BookRequirement(models.Model):
    """
    A "Wanted Book" requirement — a user is looking for a specific book.
    This is separate from the marketplace BookListing (supply side).
    """

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        LIKE_NEW = "LIKE_NEW", "Like New"
        GOOD = "GOOD", "Good"
        ACCEPTABLE = "ACCEPTABLE", "Acceptable"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FULFILLED = "FULFILLED", "Fulfilled"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="book_requirements",
        db_index=True,
    )
    book_title = models.CharField(max_length=255, db_index=True)
    preferred_condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.GOOD,
    )
    min_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    max_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Book Requirement"
        verbose_name_plural = "Book Requirements"

    def __str__(self):
        return f"Wanted: {self.book_title} by {self.user.full_name}"
