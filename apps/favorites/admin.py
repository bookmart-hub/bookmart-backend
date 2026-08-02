from django.contrib import admin

from apps.marketplace.models import Wishlist


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "listing",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "user__email",
        "user__full_name",
        "listing__book__title",
        "listing__seller__email",
        "listing__seller__full_name",
    )
    ordering = ("-created_at",)
    list_select_related = ("user", "listing", "listing__book", "listing__seller")
    readonly_fields = ("user", "listing", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
