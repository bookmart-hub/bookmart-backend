from django.contrib import admin

from apps.books.models import Author, Book, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'created_at')
    search_fields = ('name',)
    # Automatically generates slugs as you type names
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'isbn_13', 'publisher', 'created_at')
    search_fields = ('title', 'isbn_13', 'authors')
    list_filter = ('categories', 'created_at')


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'rating')
    search_fields = ('name', 'designation')
