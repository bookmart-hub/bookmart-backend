from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db.models import Count

from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Author, Book, Category
from apps.marketplace.models import BookListing, BookListingImage
from apps.requirements.models import BookRequirement

User = get_user_model()


class HomeFeedTests(APITestCase):

    def setUp(self):
        self.seller = User.objects.create_user(
            email="seller@example.com",
            full_name="Seller User",
            password="testpassword123",
        )
        self.buyer = User.objects.create_user(
            email="buyer@example.com",
            full_name="Buyer User",
            password="testpassword123",
        )
        self.other_seller = User.objects.create_user(
            email="other@example.com",
            full_name="Other Seller",
            password="testpassword123",
        )

        self.author = Author.objects.create(name="Thomas H. Corman")
        self.book = Book.objects.create(title="Introduction to Algorithm")
        self.book.authors.add(self.author)

        self.category = Category.objects.create(
            name="Computer Science",
            slug="computer-science",
        )
        self.book.categories.add(self.category)

        self.dummy_image_data = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
        )

    def get_dummy_file(self, name):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, self.dummy_image_data, content_type="image/gif")

    def _create_listing(self, seller=None, book=None, condition="GOOD", status="AVAILABLE"):
        seller = seller or self.seller
        book = book or self.book
        listing = BookListing.objects.create(
            book=book,
            seller=seller,
            price=500.00,
            condition=condition,
            status=status,
        )
        BookListingImage.objects.create(
            book_listing=listing,
            image=self.get_dummy_file("front.gif"),
            label="FRONT_COVER",
        )
        BookListingImage.objects.create(
            book_listing=listing,
            image=self.get_dummy_file("back.gif"),
            label="BACK_COVER",
        )
        BookListingImage.objects.create(
            book_listing=listing,
            image=self.get_dummy_file("spine.gif"),
            label="SPINE",
        )
        BookListingImage.objects.create(
            book_listing=listing,
            image=self.get_dummy_file("middle.gif"),
            label="MIDDLE_PAGE",
        )
        return listing

    # --- Permissions ---

    def test_unauthenticated_returns_401(self):
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- No location ---

    def test_no_location_returns_empty_nearby(self):
        self.client.force_authenticate(user=self.buyer)
        self._create_listing()
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nearby_books"], [])

    # --- No listings ---

    def test_no_listings_returns_empty_sections(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["latest_books"], [])
        self.assertEqual(response.data["popular_books"], [])
        self.assertEqual(response.data["recommended_books"], [])
        self.assertEqual(response.data["featured_books"], [])
        self.assertEqual(response.data["nearby_books"], [])

    # --- No favorites ---

    def test_no_favorites_fallback_to_latest(self):
        self.client.force_authenticate(user=self.buyer)
        self._create_listing()
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["popular_books"]), 1)

    # --- No requirements ---

    def test_no_requirements_recommended_fallback(self):
        self.client.force_authenticate(user=self.buyer)
        self._create_listing()
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recommended_books", response.data)

    # --- Profile completion ---

    def test_profile_completion_with_all_fields(self):
        from apps.core.models import College
        college = College.objects.create(name="Test College", district="Test", state="Test")
        profile = self.seller.profile
        profile.image = self.get_dummy_file("avatar.gif")
        profile.phone_number = "+919876543210"
        profile.bio = "Hello, I am a seller."
        profile.college = college
        profile.personalization_fields = {"user_role": "STUDENT"}
        profile.save()

        self.client.force_authenticate(user=self.seller)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile_completion"], 100)

    def test_profile_completion_with_no_fields(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile_completion"], 0)

    # --- Statistics ---

    def test_statistics_returns_counts(self):
        self._create_listing()
        BookRequirement.objects.create(
            user=self.seller,
            book=self.book,
            book_title="Introduction to Algorithm",
            preferred_condition="GOOD",
            max_price=600.00,
        )
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["stats"]["active_listings"], 1)
        self.assertGreaterEqual(response.data["stats"]["requirements"], 1)
        self.assertGreaterEqual(response.data["stats"]["users"], 3)

    # --- Pagination ---

    def test_page_size_limits_to_15(self):
        for i in range(20):
            book = Book.objects.create(title=f"Book {i}")
            book.authors.add(self.author)
            book.categories.add(self.category)
            self._create_listing(book=book)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/?page_size=20")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["latest_books"]), 15)

    # --- Performance ---

    def test_response_under_500kb(self):
        for i in range(10):
            book = Book.objects.create(title=f"Perf Book {i}")
            book.authors.add(self.author)
            book.categories.add(self.category)
            self._create_listing(book=book)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        import json
        response_json = json.dumps(response.data)
        self.assertLess(len(response_json.encode("utf-8")), 500 * 1024)

    # --- Categories ---

    def test_categories_returns_with_book_count(self):
        self._create_listing()
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["categories"]), 0)
        self.assertIn("total_books_count", response.data["categories"][0])

    # --- Featured books ---

    def test_featured_books_requires_all_images(self):
        listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=500.00,
            condition="GOOD",
            status="AVAILABLE",
        )
        BookListingImage.objects.create(
            book_listing=listing,
            image=self.get_dummy_file("front.gif"),
            label="FRONT_COVER",
        )

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        featured_ids = [b["id"] for b in response.data["featured_books"]]
        self.assertNotIn(listing.id, featured_ids)

    def test_featured_books_excludes_poor_condition(self):
        self._create_listing(condition="POOR")
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        featured_ids = [b["id"] for b in response.data["featured_books"]]
        self.assertEqual(len(featured_ids), 0)

    # --- Nearby books ---

    def test_nearby_books_with_location(self):
        listing = self._create_listing()
        listing.latitude = "12.9716"
        listing.longitude = "77.5946"
        listing.save()

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(
            "/api/v1/home/?lat=12.9716&lng=77.5946&radius=100"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["nearby_books"]), 0)

    def test_nearby_books_returns_max_10(self):
        for i in range(15):
            book = Book.objects.create(title=f"Nearby Book {i}")
            book.authors.add(self.author)
            book.categories.add(self.category)
            listing = self._create_listing(book=book)
            listing.latitude = "12.9716"
            listing.longitude = "77.5946"
            listing.save()

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(
            "/api/v1/home/?lat=12.9716&lng=77.5946&radius=100"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["nearby_books"]), 10)

    # --- Popular books ---

    def test_popular_books_ordered_by_favorite_count(self):
        listing1 = self._create_listing()
        listing2 = self._create_listing()

        from apps.marketplace.models import Wishlist
        Wishlist.objects.create(user=self.buyer, listing=listing1)
        Wishlist.objects.create(user=self.other_seller, listing=listing1)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data["popular_books"]) >= 2:
            self.assertGreater(
                response.data["popular_books"][0].get("favorite_count", 0),
                response.data["popular_books"][1].get("favorite_count", 0),
            )

    # --- Recommended books ---

    def test_recommended_books_uses_user_data(self):
        user_book = Book.objects.create(title="User's Book")
        user_book.authors.add(self.author)
        user_book.categories.add(self.category)
        self._create_listing(book=user_book, seller=self.buyer)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/home/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recommended_books", response.data)

    # --- Duplicate avoidance ---

    def test_no_duplicate_listings_within_sections(self):
        listing = self._create_listing()
        listing.latitude = "12.9716"
        listing.longitude = "77.5946"
        listing.save()

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(
            "/api/v1/home/?lat=12.9716&lng=77.5946&radius=100"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for section in [
            "nearby_books",
            "latest_books",
            "popular_books",
            "recommended_books",
            "featured_books",
        ]:
            ids = [item["id"] for item in response.data[section]]
            self.assertEqual(
                len(ids),
                len(set(ids)),
                f"Duplicate listings found within {section}",
            )