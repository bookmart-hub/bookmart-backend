from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.authentication.models import College, EmailOTP, Profile, User


class UserAdmin(BaseUserAdmin):
    # Control structural grids displayed in lists
    list_display = ('email', 'username', 'provider',
                    'email_verified', 'is_staff')
    list_filter = ('is_staff', 'provider', 'email_verified')

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('OAuth Tracking', {
         'fields': ('provider', 'provider_id', 'email_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
    )

    search_fields = ('email', 'username')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')


admin.site.register(User, UserAdmin)
admin.site.register(Profile)
admin.site.register(College)
admin.site.register(EmailOTP)
