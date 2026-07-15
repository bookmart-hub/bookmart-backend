from decimal import Decimal

from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """
    Hierarchical structural nodes for filtering books (e.g., Fiction, Exam Prep).
    Implements optimized slug lookups for fast Next.js URL paths.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Emoji character or Lucide icon string lookup key (e.g., '🚀')",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Author(models.Model):
    """New model backing screens 11 and 12"""

    name = models.CharField(max_length=255, unique=True)
    designation = models.CharField(
        max_length=100, default="Author", help_text="e.g., Novelist, Poet"
    )
    bio = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal(4.0))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    """
    The immutable core catalog master entry. Multiple sellers will link
    their physical variable listings back to a single record here.
    """

    openlibrary_key = models.CharField(
        max_length=100, unique=True, null=True, blank=True, db_index=True
    )
    isbn_13 = models.CharField(
        max_length=13, unique=True, null=True, blank=True, db_index=True
    )
    isbn_10 = models.CharField(max_length=10, null=True, blank=True, db_index=True)

    openlibrary_id = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )
    google_books_id = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )

    title = models.CharField(max_length=255, db_index=True)
    authors = models.ManyToManyField(Author, related_name="books")
    description = models.TextField(blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=50, blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    categories = models.ManyToManyField(Category, related_name="books")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ExternalBookSource(models.Model):
    SOURCE_CHOICES = (
        ("openlibrary", "Open Library"),
        ("google_books", "Google Books"),
    )
    book = models.OneToOneField(
        Book, on_delete=models.CASCADE, related_name="external_source"
    )
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
