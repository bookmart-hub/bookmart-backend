from django.contrib import admin
from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "reviewer", "seller", "listing", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["reviewer__email", "seller__email", "listing__book__title", "review"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
