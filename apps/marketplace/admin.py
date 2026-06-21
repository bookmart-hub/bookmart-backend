from django.contrib import admin

from apps.marketplace.models import (
    BookRequirement,
    Listing,
    ListingAnalyticsDaily,
    PlatformReport,
)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'seller', 'price',
                    'condition', 'status', 'created_at')
    list_filter = ('condition', 'status', 'created_at')
    search_fields = ('book__title', 'seller__username', 'seller__email')
    # Keeps spatial coordinate entries secure
    readonly_fields = ('latitude', 'longitude')


@admin.register(BookRequirement)
class BookRequirementAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'user', 'min_budget',
                    'max_budget', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('book__title', 'user__username', 'user__email')


@admin.register(ListingAnalyticsDaily)
class ListingAnalyticsDailyAdmin(admin.ModelAdmin):
    list_display = ('listing', 'date', 'views_count',
                    'clicks_count', 'wa_contacts_count')
    list_filter = ('date',)
    date_hierarchy = 'date'  # Adds a neat horizontal time-navigation filter widget


@admin.register(PlatformReport)
class PlatformReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'report_type',
                    'category', 'is_reviewed', 'created_at')
    list_filter = ('report_type', 'category', 'is_reviewed', 'created_at')
    search_fields = ('reporter__username', 'details')
    actions = ['mark_as_reviewed']

    @admin.action(description='Mark selected reports as reviewed')
    def mark_as_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True)
