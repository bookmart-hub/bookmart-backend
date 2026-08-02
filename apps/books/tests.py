from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Category, Book, Author
from apps.books.services import import_book_from_openlibrary

User = get_user_model()


class BookImportCategorizationTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="importer@example.com",
            full_name="Importer User",
            password="testpassword123",
        )

    @patch("apps.books.services.get_book_document")
    @patch("apps.books.services.get_author_document")
    def test_import_book_categorization(
        self, mock_get_author_document, mock_get_book_document
    ):
        mock_get_book_document.return_value = {
            "title": "Introduction to Algorithms",
            "covers": [12345],
            "authors": [{"author": {"key": "/authors/OL26346A"}}],
            "subjects": ["Algorithms", "Computer programming", "Mathematics"],
            "first_publish_date": "1990",
        }
        mock_get_author_document.return_value = {"name": "Thomas H. Cormen"}

        book, created = import_book_from_openlibrary("/works/OL27448W")

        self.assertTrue(created)
        self.assertEqual(book.title, "Introduction to Algorithms")
        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.authors.first().name, "Thomas H. Cormen")
        self.assertEqual(book.published_date, date(1990, 1, 1))

        self.assertEqual(book.categories.count(), 3)
        categories = list(book.categories.values_list("name", flat=True))
        self.assertIn("Algorithms", categories)
        self.assertIn("Computer programming", categories)
        self.assertIn("Mathematics", categories)

        algorithms_cat = Category.objects.get(name="Algorithms")
        self.assertEqual(algorithms_cat.slug, "algorithms")

        dup_cat = Category(name="Algorithms.")
        dup_cat.save()
        self.assertEqual(dup_cat.slug, "algorithms-1")

    @patch("apps.books.services.get_book_document")
    @patch("apps.books.services.get_author_document")
    def test_import_book_without_covers(
        self, mock_get_author_document, mock_get_book_document
    ):
        mock_get_book_document.return_value = {
            "title": "Batman the Killing Joke",
            "authors": [{"author": {"key": "/authors/OL26346A"}}],
            "subjects": ["Comics"],
            "first_publish_date": "1988 July",
        }
        mock_get_author_document.return_value = {"name": "Alan Moore"}

        book, created = import_book_from_openlibrary("/works/OL43079896W")

        self.assertTrue(created)
        self.assertEqual(book.title, "Batman the Killing Joke")
        self.assertEqual(book.cover_url, "")
        self.assertEqual(book.published_date, date(1988, 1, 1))

    @patch("apps.books.services.get_book_document")
    @patch("apps.books.services.get_author_document")
    def test_import_book_endpoint_payload(
        self, mock_get_author_document, mock_get_book_document
    ):
        """Verify POST endpoint response payload is extended with published_year, authors, and categories."""
        self.client.force_authenticate(user=self.user)
        mock_get_book_document.return_value = {
            "title": "Introduction to Algorithms",
            "covers": [12345],
            "authors": [{"author": {"key": "/authors/OL26346A"}}],
            "subjects": ["Algorithms", "Mathematics"],
            "first_publish_date": "1990",
        }
        mock_get_author_document.return_value = {"name": "Thomas H. Cormen"}

        url = "/api/v1/book/import-openlibrary/"
        data = {"openlibrary_key": "/works/OL27448W"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Introduction to Algorithms")
        self.assertEqual(response.data["published_year"], 1990)
        self.assertEqual(response.data["authors"], ["Thomas H. Cormen"])
        self.assertEqual(response.data["categories"], ["Algorithms", "Mathematics"])

    @patch("apps.books.services.get_book_document")
    @patch("apps.books.services.get_author_document")
    def test_import_book_with_custom_category(
        self, mock_get_author_document, mock_get_book_document
    ):
        """Verify importing a book with a custom manual category attaches the custom category."""
        self.client.force_authenticate(user=self.user)
        mock_get_book_document.return_value = {
            "title": "Clean Code",
            "authors": [{"author": {"key": "/authors/OL1234A"}}],
            "subjects": ["Software"],
            "first_publish_date": "2008",
        }
        mock_get_author_document.return_value = {"name": "Robert C. Martin"}

        url = "/api/v1/book/import-openlibrary/"
        data = {
            "openlibrary_key": "/works/OL12345W",
            "category": "Software Engineering Custom",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Software Engineering Custom", response.data["categories"])
        self.assertIn("Software", response.data["categories"])

    def test_manual_book_create_endpoint(self):
        """Verify manually inserting a book record when search does not find the book."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/book/manual/"
        data = {
            "title": "My Custom Unique Book",
            "author": "John Doe",
            "category": "Self Help Custom",
            "published_year": 2024,
            "description": "A great unique book.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "My Custom Unique Book")
        self.assertEqual(response.data["authors"], ["John Doe"])
        self.assertIn("Self Help Custom", response.data["categories"])
        self.assertTrue(response.data["is_local"])

    @patch("apps.books.services.requests.get")
    def test_search_books_returns_local_records(self, mock_requests_get):
        """Verify searching returns locally stored books and external OpenLibrary results."""
        self.client.force_authenticate(user=self.user)

        # Pre-create local book manually
        manual_url = "/api/v1/book/manual/"
        self.client.post(
            manual_url,
            {
                "title": "Python Deep Learning",
                "author": "Jane Smith",
                "category": "Artificial Intelligence",
            },
            format="json",
        )

        mock_response = patch("requests.get").start()
        mock_response.return_value.json.return_value = {"docs": []}

        search_url = "/api/v1/book/search/?q=Python"
        response = self.client.get(search_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        local_book = next(b for b in response.data if b["title"] == "Python Deep Learning")
        self.assertTrue(local_book["is_local"])
        self.assertEqual(local_book["authors"], ["Jane Smith"])
        self.assertIn("Artificial Intelligence", local_book["categories"])

    @patch("apps.books.services.requests.get")
    def test_search_books_local_first_does_not_call_openlibrary(self, mock_requests_get):
        """Ensure that if local database produces results, OpenLibrary is not called."""
        self.client.force_authenticate(user=self.user)

        manual_url = "/api/v1/book/manual/"
        self.client.post(
            manual_url,
            {
                "title": "Django Web Development",
                "author": "Alice Developer",
            },
            format="json",
        )

        search_url = "/api/v1/book/search/?q=Django"
        response = self.client.get(search_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Django Web Development")
        self.assertTrue(response.data[0]["is_local"])

        mock_requests_get.assert_not_called()


class CategoryViewSetTests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="seller1@example.com",
            full_name="Seller One",
            password="testpassword123",
        )
        self.user2 = User.objects.create_user(
            email="seller2@example.com",
            full_name="Seller Two",
            password="testpassword123",
        )
        self.category = Category.objects.create(
            name="Competitive Exams",
            subtitle="Prepare to Succeed",
            icon="🚀",
        )

        manual_url = "/api/v1/book/manual/"
        self.client.force_authenticate(user=self.user1)
        res = self.client.post(
            manual_url,
            {
                "title": "Quantitative Aptitude",
                "author": "R.S. Aggarwal",
                "category": "Competitive Exams",
            },
            format="json",
        )
        self.book_id = res.data["book_id"]

        from apps.books.models import Book
        from apps.marketplace.models import BookListing

        book = Book.objects.get(id=self.book_id)

        # Listing 1: Price 500
        self.listing_500 = BookListing.objects.create(
            book=book,
            seller=self.user1,
            price="500.00",
            condition="GOOD",
            status="AVAILABLE",
        )
        # Listing 2: Price 400 (cheapest)
        self.listing_400 = BookListing.objects.create(
            book=book,
            seller=self.user2,
            price="400.00",
            condition="LIKE_NEW",
            status="AVAILABLE",
        )

    def test_list_categories(self):
        """Ensure GET /api/v1/book/categories/ returns list of categories with total_books_count and subtitle."""
        url = "/api/v1/book/categories/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Competitive Exams")
        self.assertEqual(response.data["results"][0]["subtitle"], "Prepare to Succeed")

    def test_retrieve_category_detail_ranked_by_price(self):
        """Ensure retrieving category returns canonical books with listings ranked by price ascending (cheapest first)."""
        url = f"/api/v1/book/categories/{self.category.slug}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Competitive Exams")
        self.assertEqual(response.data["subtitle"], "Prepare to Succeed")

        books = response.data["books"]
        self.assertEqual(len(books), 1)

        quant_book = books[0]
        self.assertEqual(quant_book["title"], "Quantitative Aptitude")
        self.assertEqual(quant_book["authors"], ["R.S. Aggarwal"])
        self.assertEqual(quant_book["lowest_price"], "400.00")
        self.assertEqual(quant_book["total_listings_count"], 2)
        self.assertEqual(quant_book["cheapest_listing"]["price"], "400.00")

        # Verify listings are ordered ascending by price: 400.00 then 500.00
        listings = quant_book["listings"]
        self.assertEqual(len(listings), 2)
        self.assertEqual(listings[0]["price"], "400.00")
        self.assertEqual(listings[1]["price"], "500.00")


class BookViewSetTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            full_name="Buyer User",
            password="testpassword123",
        )
        self.category = Category.objects.create(
            name="Competitive Exams",
            subtitle="Prepare to Succeed",
            icon="🚀",
        )
        self.other_category = Category.objects.create(
            name="Fiction",
            subtitle="Explore Worlds",
            icon="📚",
        )

        from apps.books.models import Book
        self.book1 = Book.objects.create(
            title="Quantitative Aptitude",
            published_date=date(2020, 1, 1),
        )
        self.book1.categories.add(self.category)

        self.book2 = Book.objects.create(
            title="A Song of Ice and Fire",
            published_date=date(1996, 8, 1),
        )
        self.book2.categories.add(self.other_category)

    def test_list_books_paginated(self):
        """Ensure GET /api/v1/book/books/ returns paginated books."""
        url = "/api/v1/book/books/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_filter_books_by_category_slug(self):
        """Ensure GET /api/v1/book/books/?categories__slug=... filters books."""
        url = "/api/v1/book/books/?categories__slug=competitive-exams"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Quantitative Aptitude")

    def test_search_books(self):
        """Ensure GET /api/v1/book/books/?search=... searches books by title."""
        url = "/api/v1/book/books/?search=Song"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "A Song of Ice and Fire")

    def test_retrieve_book(self):
        """Ensure GET /api/v1/book/books/{id}/ returns book details."""
        url = f"/api/v1/book/books/{self.book1.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Quantitative Aptitude")


class AuthorViewSetTests(APITestCase):

    def setUp(self):
        self.author1 = Author.objects.create(name="Author One", designation="Novelist", bio="Bio one")
        self.author2 = Author.objects.create(name="Author Two", designation="Poet", bio="Bio two")

    def test_list_authors(self):
        url = "/api/v1/book/authors/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["name"], "Author One")

    def test_retrieve_author(self):
        url = f"/api/v1/book/authors/{self.author1.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Author One")



