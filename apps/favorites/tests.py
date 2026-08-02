from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Author, Book
from apps.marketplace.models import BookListing, BookListingImage, Wishlist
from apps.authentication.models import User


class FavoriteAPITests(APITestCase):

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
        self.other_user = User.objects.create_user(
            email="other@example.com",
            full_name="Other User",
            password="testpassword123",
        )

        self.author = Author.objects.create(name="Thomas H. Corman")
        self.book = Book.objects.create(title="Introduction to Algorithm")
        self.book.authors.add(self.author)

        self.listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=600.00,
            condition="GOOD",
            status="AVAILABLE",
        )
        BookListingImage.objects.create(
            book_listing=self.listing,
            image=self._get_dummy_file("front.gif"),
            label="FRONT_COVER",
        )

        self.sold_listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=500.00,
            condition="GOOD",
            status="SOLD",
        )

        self.pending_listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=400.00,
            condition="GOOD",
            status="PENDING",
        )

    def _get_dummy_file(self, name):
        dummy_data = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
        )
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, dummy_data, content_type="image/gif")

    # ── Add favorite ──
    def test_add_favorite_success(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": self.listing.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["detail"], "Listing saved successfully.")
        self.assertTrue(
            Wishlist.objects.filter(user=self.buyer, listing=self.listing).exists()
        )

    # ── Duplicate favorite returns 409 ──
    def test_add_favorite_duplicate_returns_409(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": self.listing.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already in your favorites", response.data["detail"])

    # ── Cannot favorite own listing ──
    def test_cannot_favorite_own_listing(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": self.listing.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Cannot favorite your own listing", response.data["detail"])

    # ── Cannot favorite sold listing ──
    def test_cannot_favorite_sold_listing(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": self.sold_listing.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not available", response.data["detail"])

    # ── Cannot favorite pending listing ──
    def test_cannot_favorite_pending_listing(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": self.pending_listing.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not available", response.data["detail"])

    # ── Favorite non-existent listing returns 404 ──
    def test_favorite_nonexistent_listing_returns_404(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": 99999},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.data["detail"])

    # ── Anonymous cannot add favorite ──
    def test_anonymous_cannot_add_favorite(self):
        response = self.client.post(
            "/api/v1/favorites/",
            {"listing": self.listing.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Anonymous cannot check favorite ──
    def test_anonymous_cannot_check_favorite(self):
        response = self.client.get(
            f"/api/v1/favorites/check/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Delete favorite ──
    def test_delete_favorite_success(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_authenticate(user=self.buyer)
        response = self.client.delete(
            f"/api/v1/favorites/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Wishlist.objects.filter(user=self.buyer, listing=self.listing).exists()
        )

    # ── Delete non-existent favorite returns 404 ──
    def test_delete_nonexistent_favorite_returns_404(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.delete(
            f"/api/v1/favorites/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not in favorites", response.data["detail"])

    # ── List favorites ──
    def test_list_favorites(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/favorites/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.listing.id)

    # ── List favorites returns only user's favorites ──
    def test_list_favorites_returns_only_user_favorites(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        Wishlist.objects.create(user=self.other_user, listing=self.listing)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/favorites/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    # ── List favorites newest first ──
    def test_list_favorites_newest_first(self):
        other_listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=300.00,
            condition="GOOD",
            status="AVAILABLE",
        )
        Wishlist.objects.create(user=self.buyer, listing=other_listing)
        Wishlist.objects.create(user=self.buyer, listing=self.listing)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/favorites/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["id"], self.listing.id)
        self.assertEqual(results[1]["id"], other_listing.id)

    # ── Check favorite endpoint ──
    def test_check_favorite_returns_true(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(
            f"/api/v1/favorites/check/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["saved"])

    # ── Check favorite returns false ──
    def test_check_favorite_returns_false(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(
            f"/api/v1/favorites/check/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["saved"])

    # ── Anonymous cannot check favorite ──
    def test_anonymous_cannot_check_favorite(self):
        response = self.client.get(
            f"/api/v1/favorites/check/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Favorite count endpoint ──
    def test_favorite_count(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        Wishlist.objects.create(user=self.other_user, listing=self.listing)
        response = self.client.get(
            f"/api/v1/favorites/count/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    # ── Favorite count zero ──
    def test_favorite_count_zero(self):
        response = self.client.get(
            f"/api/v1/favorites/count/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    # ── Favorite count is public ──
    def test_favorite_count_is_public(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        response = self.client.get(
            f"/api/v1/favorites/count/{self.listing.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Pagination ──
    def test_list_favorites_pagination(self):
        for i in range(5):
            listing = BookListing.objects.create(
                book=self.book,
                seller=self.seller,
                price=100 + i,
                condition="GOOD",
                status="AVAILABLE",
            )
            Wishlist.objects.create(user=self.buyer, listing=listing)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/favorites/?page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)
        self.assertIsNotNone(response.data["next"])

    # ── Listing response includes is_favorited and favorite_count ──
    def test_listing_response_includes_favorite_fields(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/marketplace/listings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        target = next((r for r in results if r["id"] == self.listing.id), None)
        self.assertIsNotNone(target)
        self.assertTrue(target["is_favorited"])
        self.assertEqual(target["favorite_count"], 1)

    # ── Listing response is_favorited false for other user ──
    def test_listing_response_is_favorited_false_for_other_user(self):
        Wishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/v1/marketplace/listings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        target = next((r for r in results if r["id"] == self.listing.id), None)
        self.assertIsNotNone(target)
        self.assertFalse(target["is_favorited"])
        self.assertEqual(target["favorite_count"], 1)