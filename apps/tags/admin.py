from django.contrib import admin
from apps.tags.models import Tag, TaggedItem


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
    readonly_fields = ["created_at"]
    ordering = ["name"]


@admin.register(TaggedItem)
class TaggedItemAdmin(admin.ModelAdmin):
    list_display = ["id", "tag", "content_type", "object_id", "content_object", "created_at"]
    list_filter = ["content_type", "created_at"]
    search_fields = ["tag__name", "object_id"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
