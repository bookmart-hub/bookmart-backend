from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reporter",
        "report_type",
        "reason",
        "status",
        "created_at",
    )
    list_filter = ("status", "report_type", "reason", "created_at")
    search_fields = (
        "reporter__email",
        "reporter__full_name",
        "reported_user__email",
        "reported_user__full_name",
    )
    readonly_fields = (
        "reporter",
        "report_type",
        "reported_user",
        "reported_listing",
        "reason",
        "details",
        "created_at",
    )
    fieldsets = (
        (
            "Original Report (read-only)",
            {
                "fields": (
                    "reporter",
                    "report_type",
                    "reported_user",
                    "reported_listing",
                    "reason",
                    "details",
                    "created_at",
                )
            },
        ),
        (
            "Review",
            {
                "fields": ("status", "review_notes"),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

