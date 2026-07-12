# from django.contrib import admin
# from django.contrib.auth import get_user_model

# # from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# # from django.contrib.auth.models import Group as BaseGroup
# from import_export.admin import ImportExportModelAdmin

# from apps.core.models import College, Profile, User

# BaseUser = get_user_model()


# # @admin.register(User)
# class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
#     list_display = ("email", "provider", "email_verified", "is_staff")
#     list_filter = ("is_staff", "provider", "email_verified")
#     search_fields = ("email",)
#     ordering = ("email",)
#     filter_horizontal = ("groups", "user_permissions")


# @admin.register(College)
# class CollegeAdmin(ImportExportModelAdmin):
#     # resource_classes = [CollegeResource]

#     list_display = ("name", "district", "state", "created_at")
#     list_filter = ("state", "district")
#     search_fields = ("name", "district")
#     ordering = ("name",)


# # Unregister the default Group model to avoid duplicates
# admin.site.unregister(BaseUser, BaseUserAdmin)
# # admin.site.unregister(BaseGroup, BaseGroupAdmin)

# # Register your custom user model and group
# admin.site.register(User, UserAdmin)

# admin.site.register(Profile)


from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from apps.core.models import College, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "college",
        "city_location",
    )

    search_fields = (
        "user__email",
        "user__full_name",
        "phone_number",
    )

    list_filter = (
        "college",
        "city_location",
    )

    autocomplete_fields = (
        "user",
        "college",
    )


@admin.register(College)
class CollegeAdmin(ImportExportModelAdmin):
    list_display = (
        "id",
        "name",
        "district",
        "state",
        "created_at",
    )

    search_fields = (
        "id",
        "name",
        "district",
        "state",
    )

    list_filter = (
        "state",
        "district",
    )

    ordering = (
        "id",
        "state",
        "district",
        "name",
    )

    date_hierarchy = "created_at"
