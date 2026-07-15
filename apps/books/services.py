from datetime import date

import requests
from django.db import transaction

from apps.books.models import Author, Book

OPENLIBRARY_WORK_URL = "https://openlibrary.org"
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


def parse_description(description):
    if isinstance(description, dict):
        return description.get("value", "")

    return description or ""


@transaction.atomic
def import_book_from_openlibrary(work_key):
    document = get_book_document(work_key)
    title = document.get("title")
    covers = document.get("covers", [])
    cover_url = None

    if covers:
        cover_url = f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"

    author_objects = []

    for author_data in document.get("authors", []):
        author_key = author_data.get("author", {}).get("key")

        if not author_key:
            continue

        # Fetch author details
        author_document = get_author_document(author_key)
        author_name = author_document.get("name", "Unknown")
        author, _ = Author.objects.get_or_create(name=author_name)
        author_objects.append(author)

    book, created = Book.objects.update_or_create(
        openlibrary_key=work_key,
        defaults={
            "title": title,
            "cover_url": cover_url,
        },
    )

    # ✅ ManyToMany assignment
    book.authors.set(author_objects)

    return book, created


def get_book_document(work_key: str):
    """
    Fetch complete OpenLibrary work document.
    Example:
    /works/OL27448W
    """

    url = f"{OPENLIBRARY_WORK_URL}{work_key}.json"
    response = requests.get(
        url,
        timeout=5,
    )
    response.raise_for_status()

    return response.json()


def get_author_document(author_key):
    url = f"https://openlibrary.org/{author_key}.json"
    response = requests.get(url, timeout=5)
    response.raise_for_status()

    return response.json()


def search_books(query: str, limit: int = 10):
    params = {
        "q": query,
        "limit": limit,
        "fields": "key,title,author_name,isbn,first_publish_year,cover_i",
    }
    response = requests.get(
        OPENLIBRARY_SEARCH_URL,
        params=params,
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()

    results = []

    for book in data.get("docs", []):
        isbn = book.get("isbn", [])

        # Prefer ISBN-13
        isbn13 = next(
            (code for code in isbn if len(code) == 13 and code.startswith("978")),
            None,
        )
        cover_id = book.get("cover_i")
        results.append(
            {
                "openlibrary_key": book.get("key"),
                "title": book.get("title"),
                "authors": book.get("author_name", []),
                "isbn13": isbn13,
                "published_year": book.get("first_publish_year"),
                "cover_image": (
                    f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                    if cover_id
                    else None
                ),
            }
        )

    return results


def import_openlibrary_book(data):

    authors = []

    for author_name in data.get("author_name", []):
        author, _ = Author.objects.get_or_create(name=author_name.strip())
        authors.append(author)

    isbn13 = None
    isbn10 = None

    for isbn in data.get("isbn", []):
        if len(isbn) == 13:
            isbn13 = isbn
            break

    for isbn in data.get("isbn", []):
        if len(isbn) == 10:
            isbn10 = isbn
            break

    # Try finding existing book
    book = None

    if isbn13:
        book = Book.objects.filter(isbn_13=isbn13).first()

    if not book:
        book = Book.objects.create(
            isbn_13=isbn13,
            isbn_10=isbn10,
            title=data["title"],
            published_date=(
                date(data["publish_year"], 1, 1) if data.get("publish_year") else None
            ),
            cover_url=(
                f"https://covers.openlibrary.org/b/id/{data['cover_id']}-L.jpg"
                if data.get("cover_id")
                else ""
            ),
            openlibrary_id=data.get("key"),
        )

    if authors:
        book.authors.set(authors)

    return book
