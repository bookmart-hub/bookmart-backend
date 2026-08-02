from django.conf import settings
from django.db import models

from apps.books.models import Book


# Condition hierarchy for matching: higher index = better condition
_CONDITION_ORDER = [
    'ACCEPTABLE',
    'FAIR',
    'GOOD',
    'LIKE_NEW',
    'NEW',
]


def condition_meets_requirement(listing_condition, required_condition):
    '''
    Return True if listing_condition is at least as good as required_condition.
    Example: required GOOD matches NEW, LIKE_NEW, GOOD but not FAIR/POOR.
    '''
    try:
        listing_idx = _CONDITION_ORDER.index(listing_condition)
        required_idx = _CONDITION_ORDER.index(required_condition)
        return listing_idx >= required_idx
    except ValueError:
        return False


class BookRequirement(models.Model):
    '''
    A 'Wanted Book' requirement — a user is looking for a specific book.
    This is separate from the marketplace BookListing (supply side).
    '''

    class Condition(models.TextChoices):
        NEW = 'NEW', 'New'
        LIKE_NEW = 'LIKE_NEW', 'Like New'
        GOOD = 'GOOD', 'Good'
        ACCEPTABLE = 'ACCEPTABLE', 'Acceptable'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        FULFILLED = 'FULFILLED', 'Fulfilled'
        CANCELLED = 'CANCELLED', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='book_requirements',
        db_index=True,
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        related_name='wanted_requirements',
        null=True,
        blank=True,
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
    notes = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Book Requirement'
        verbose_name_plural = 'Book Requirements'

    def __str__(self):
        title = self.book.title if self.book_id else self.book_title
        return f'Wanted: {title} by {self.user.full_name}'
