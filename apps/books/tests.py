from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Category
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
