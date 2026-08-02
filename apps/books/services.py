from datetime import date
import re

import requests
from django.db import transaction
from django.db.models import Q

from apps.books.models import Author, Book, Category

OPENLIBRARY_WORK_URL = "https://openlibrary.org"
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


def parse_description(description):
    if isinstance(description, dict):
        return description.get("value", "")

    return description or ""


def parse_first_publish_date(date_str):
    if not date_str:
        return None
    match = re.search(r"\b\d{4}\b", str(date_str))
    if match:
        year = int(match.group(0))
        return date(year, 1, 1)
    return None


def process_category_input(category_input):
    """
    Parses string or list input into Category model instances.
    Accepts single string (e.g. 'Fiction' or 'Fiction, Exam Prep') or list of strings/IDs.
    """
    if not category_input:
        return []

    categories = []
    items = []

    if isinstance(category_input, str):
        items = [c.strip() for c in category_input.split(",") if c.strip()]
    elif isinstance(category_input, (list, tuple, set)):
        items = list(category_input)

    for item in items:
        if isinstance(item, Category):
            categories.append(item)
        elif isinstance(item, int):
            try:
                cat = Category.objects.get(pk=item)
                categories.append(cat)
            except Category.DoesNotExist:
                pass
        elif isinstance(item, str) and item.strip():
            name = item.strip()
            if len(name) > 100:
                name = name[:100]
            cat, _ = Category.objects.get_or_create(name=name)
            categories.append(cat)

    return categories


@transaction.atomic
def import_book_from_openlibrary(work_key, custom_category=None):
    # Check if book already exists in local database
    existing_book = Book.objects.filter(openlibrary_key=work_key).first()
    if existing_book:
        if custom_category:
            manual_cats = process_category_input(custom_category)
            for cat in manual_cats:
                existing_book.categories.add(cat)
        return existing_book, False

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

    first_publish_date_str = document.get("first_publish_date")
    published_date = parse_first_publish_date(first_publish_date_str)

    book, created = Book.objects.update_or_create(
        openlibrary_key=work_key,
        defaults={
            "title": title,
            "cover_url": cover_url or "",
            "published_date": published_date,
        },
    )

    # ManyToMany assignment
    book.authors.set(author_objects)

    # Parse and assign categories from subjects (limit to top 10)
    category_objects = []
    for subject in document.get("subjects", [])[:10]:
        subject_name = subject.strip()
        if len(subject_name) > 100:
            subject_name = subject_name[:100]
        if not subject_name:
            continue
        category, _ = Category.objects.get_or_create(name=subject_name)
        category_objects.append(category)

    # Handle manual custom category input
    if custom_category:
        manual_cats = process_category_input(custom_category)
        for cat in manual_cats:
            if cat not in category_objects:
                category_objects.append(cat)

    book.categories.set(category_objects)

    return book, created


@transaction.atomic
def create_manual_book(data):
    """
    Manually creates a Book entry in the catalog when not found in external search.
    """
    title = data.get("title", "").strip()

    author_input = data.get("authors") or data.get("author") or []
    author_names = []
    if isinstance(author_input, str):
        author_names = [a.strip() for a in author_input.split(",") if a.strip()]
    elif isinstance(author_input, (list, tuple)):
        author_names = [str(a).strip() for a in author_input if str(a).strip()]

    author_objects = []
    for name in author_names:
        author, _ = Author.objects.get_or_create(name=name)
        author_objects.append(author)

    published_year = data.get("published_year")
    published_date = None
    if published_year:
        try:
            published_date = date(int(published_year), 1, 1)
        except (ValueError, TypeError):
            pass

    book = Book.objects.create(
        title=title,
        description=data.get("description", ""),
        publisher=data.get("publisher", ""),
        published_date=published_date,
        isbn_13=data.get("isbn_13") or None,
        isbn_10=data.get("isbn_10") or None,
        cover_url=data.get("cover_url", ""),
    )

    if author_objects:
        book.authors.set(author_objects)

    cat_input = data.get("category") or data.get("categories")
    if cat_input:
        cats = process_category_input(cat_input)
        if cats:
            book.categories.set(cats)

    return book


def get_book_document(work_key: str):
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
    query_str = query.strip()
    results = []

    # 1. Search local database first
    local_books = (
        Book.objects.filter(
            Q(title__icontains=query_str)
            | Q(authors__name__icontains=query_str)
            | Q(isbn_13__icontains=query_str)
            | Q(isbn_10__icontains=query_str)
            | Q(openlibrary_key=query_str)
        )
        .prefetch_related("authors", "categories")
        .distinct()[:limit]
    )

    for b in local_books:
        results.append(
            {
                "id": b.id,
                "openlibrary_key": b.openlibrary_key,
                "title": b.title,
                "authors": [author.name for author in b.authors.all()],
                "isbn13": b.isbn_13,
                "published_year": b.published_date.year if b.published_date else None,
                "cover_url": b.cover_url or None,
                "categories": [category.name for category in b.categories.all()],
                "is_local": True,
            }
        )

    # 2. If matching books exist locally, return them without searching OpenLibrary
    if results:
        return results[:limit]

    # 3. Switch to OpenLibrary search ONLY if no local books are found
    try:
        params = {
            "q": query_str,
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

        for book in data.get("docs", []):
            ol_key = book.get("key")
            isbn = book.get("isbn", [])

            isbn13 = next(
                (code for code in isbn if len(code) == 13 and code.startswith("978")),
                None,
            )

            cover_id = book.get("cover_i")
            results.append(
                {
                    "id": None,
                    "openlibrary_key": ol_key,
                    "title": book.get("title"),
                    "authors": book.get("author_name", []),
                    "isbn13": isbn13,
                    "published_year": book.get("first_publish_year"),
                    "cover_url": (
                        f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                        if cover_id
                        else None
                    ),
                    "categories": [],
                    "is_local": False,
                }
            )
    except Exception:
        pass

    return results[:limit]


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
