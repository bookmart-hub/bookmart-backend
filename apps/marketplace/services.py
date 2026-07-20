from django.db import transaction

from apps.books.models import Author, Book
from apps.books.services import import_book_from_openlibrary, process_category_input
from apps.marketplace.models import BookListing, BookListingImage


@transaction.atomic
def create_book_listing(seller, data):
    book_id = data.get("book_id")
    openlibrary_key = data.get("openlibrary_key")
    title = data.get("title")
    author_name = data.get("author")
    custom_category = data.get("category") or data.get("categories")

    book = None

    if book_id:
        book = Book.objects.get(id=book_id)
    elif openlibrary_key:
        book = Book.objects.filter(openlibrary_key=openlibrary_key).first()
        if not book:
            book, _ = import_book_from_openlibrary(openlibrary_key, custom_category=custom_category)
    elif title and author_name:
        book = Book.objects.filter(
            title__iexact=title.strip(),
            authors__name__iexact=author_name.strip(),
        ).first()

        if not book:
            author, _ = Author.objects.get_or_create(name=author_name.strip())
            book = Book.objects.create(
                title=title.strip(),
            )
            book.authors.add(author)

    if book and custom_category:
        cats = process_category_input(custom_category)
        if cats:
            book.categories.add(*cats)

    listing = BookListing.objects.create(
        book=book,
        seller=seller,
        price=data["price"],
        condition=data["condition"],
        condition_notes=data.get("condition_notes", ""),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )

    # Process and save images with correct labels
    image_fields = {
        "front_cover": BookListingImage.ImageLabel.FRONT_COVER,
        "back_cover": BookListingImage.ImageLabel.BACK_COVER,
        "spine": BookListingImage.ImageLabel.SPINE,
        "middle_page": BookListingImage.ImageLabel.MIDDLE_PAGE,
        "damage_1": BookListingImage.ImageLabel.DAMAGE_1,
        "damage_2": BookListingImage.ImageLabel.DAMAGE_2,
    }

    for field_name, label in image_fields.items():
        file_obj = data.get(field_name)
        if file_obj:
            BookListingImage.objects.create(
                book_listing=listing,
                image=file_obj,
                label=label,
            )

    return listing
