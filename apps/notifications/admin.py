from django.contrib import admin
from apps.notifications.models import Notification, Device


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "title", "is_read", "created_at"]
    list_filter = ["type", "is_read", "created_at"]
    search_fields = ["user__email", "user__full_name", "title", "body"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "expo_push_token", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "user__full_name", "expo_push_token"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
