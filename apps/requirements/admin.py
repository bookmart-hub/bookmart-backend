from django.contrib import admin

from apps.requirements.models import BookRequirement


@admin.register(BookRequirement)
class BookRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "book_title",
        "user",
        "preferred_condition",
        "min_price",
        "max_price",
        "status",
        "created_at",
    )
    list_filter = ("status", "preferred_condition", "created_at")
    search_fields = ("book_title", "user__email", "user__full_name")
    ordering = ("-created_at",)
    list_select_related = ("user",)

