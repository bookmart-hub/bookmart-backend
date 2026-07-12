from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin

from apps.authentication.models import EmailOTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    ordering = ("email",)

    list_display = (
        "email",
        "full_name",
        "provider",
        "email_verified",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "provider",
        "email_verified",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "email",
        "full_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
    )

    filter_horizontal = (
        "groups",
        "user_permissions",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "full_name",
                    "provider",
                    "provider_id",
                    "email_verified",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(EmailOTP)
class EmailOTPAdmin(ImportExportModelAdmin):
    ordering = ("user__email",)

    list_display = (
        "user__email",
        "user",
        "code",
        "purpose",
        "expires_at",
        "is_used",
    )

    list_filter = (
        "user__email",
        "user",
        "purpose",
        "is_used",
    )

    search_fields = (
        "user__email",
        "user__full_name",
    )

    # readonly_fields = (
    #     "created_at",
    #     "updated_at",
    #     "last_login",
    # )

    # filter_horizontal = (
    #     "groups",
    #     "user_permissions",
    # )

    # fieldsets = (
    #     (
    #         None,
    #         {
    #             "fields": (
    #                 "email",
    #                 "password",
    #             )
    #         },
    #     ),
    #     (
    #         "Personal Information",
    #         {
    #             "fields": (
    #                 "full_name",
    #                 "provider",
    #                 "provider_id",
    #                 "email_verified",
    #             )
    #         },
    #     ),
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
    #     (
    #         "Important Dates",
    #         {
    #             "fields": (
    #                 "last_login",
    #                 "created_at",
    #                 "updated_at",
    #             )
    #         },
    #     ),
    # )

    # add_fieldsets = (
    #     (
    #         None,
    #         {
    #             "classes": ("wide",),
    #             "fields": (
    #                 "email",
    #                 "full_name",
    #                 "password1",
    #                 "password2",
    #                 "is_active",
    #                 "is_staff",
    #                 "is_superuser",
    #             ),
    #         },
    #     ),
    # )
