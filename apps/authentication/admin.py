from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import College, EmailOTP, Profile, User


@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    # Control structural grids displayed in lists
    list_display = ("email", "username", "provider", "email_verified", "is_staff")
    list_filter = ("is_staff", "provider", "email_verified")

    # fieldsets = (
    #     (None, {"fields": ("email", "username", "password")}),
    #     ("OAuth Tracking", {"fields": ("provider", "provider_id", "email_verified")}),
    #     (
    #         "Permissions",
    #         {
    #             "fields": (
    #                 "is_active",
    #                 "is_staff",
    #                 "is_superuser",
    #                 "groups",
    #                 "user_permissions",
    #             )
    #         },
    #     ),
    # )

    search_fields = ("email", "username")
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions")


@admin.register(College)
class CollegeAdmin(ImportExportModelAdmin):
    # resource_classes = [CollegeResource]

    list_display = ("name", "district", "state", "created_at")
    list_filter = ("state", "district")
    search_fields = ("name", "district")
    ordering = ("name",)
    # filter_horizontal = ("groups", "user_permissions")


admin.site.register(Profile)
admin.site.register(EmailOTP)
