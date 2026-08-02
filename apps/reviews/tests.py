from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Author, Book
from apps.marketplace.models import BookListing, BookListingImage
from apps.reviews.models import Review

User = get_user_model()


class ReviewAPITests(APITestCase):

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
        self.other_buyer = User.objects.create_user(
            email="other@example.com",
            full_name="Other Buyer",
            password="testpassword123",
        )

        self.author = Author.objects.create(name="Test Author")
        self.book = Book.objects.create(title="Test Book")
        self.book.authors.add(self.author)

        self.listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=500.00,
            condition="GOOD",
            status="SOLD",
        )
        BookListingImage.objects.create(
            book_listing=self.listing,
            image=self._get_dummy_file("front.gif"),
            label="FRONT_COVER",
        )

        self.review = Review.objects.create(
            reviewer=self.buyer,
            seller=self.seller,
            listing=self.listing,
            rating=5,
            review="Excellent!",
        )

    def _get_dummy_file(self, name):
        dummy_data = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
        )
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, dummy_data, content_type="image/gif")

    # â”€â”€ Create review â”€â”€

    def test_create_review_success(self):
        new_listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=600.00,
            condition="GOOD",
            status="SOLD",
        )
        BookListingImage.objects.create(
            book_listing=new_listing,
            image=self._get_dummy_file("front2.gif"),
            label="FRONT_COVER",
        )
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/reviews/",
            {"listing": new_listing.id, "rating": 5, "review": "Great book!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["rating"], 5)
        self.assertEqual(response.data["review"], "Great book!")
        self.assertEqual(response.data["seller"]["id"], self.seller.id)
        self.assertEqual(response.data["reviewer"]["id"], self.buyer.id)

    def test_create_review_duplicate_returns_400(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            "/api/v1/reviews/",
            {"listing": self.listing.id, "rating": 5, "review": "Great book!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.data.get("non_field_errors", [])
        self.assertTrue(
            any("already reviewed" in str(e).lower() for e in errors)
        )

    def test_create_review_self_review_returns_400(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(
            "/api/v1/reviews/",
            {"listing": self.listing.id, "rating": 5, "review": "Great book!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.data.get("non_field_errors", [])
        self.assertTrue(
            any("cannot review" in str(e).lower() for e in errors)
        )

    def test_create_review_invalid_rating_returns_400(self):
        self.client.force_authenticate(user=self.other_buyer)
        response = self.client.post(
            "/api/v1/reviews/",
            {"listing": self.listing.id, "rating": 6, "review": "Great book!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_rating_below_1_returns_400(self):
        self.client.force_authenticate(user=self.other_buyer)
        response = self.client.post(
            "/api/v1/reviews/",
            {"listing": self.listing.id, "rating": 0, "review": "Bad book!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_unauthenticated_returns_401(self):
        response = self.client.post(
            "/api/v1/reviews/",
            {"listing": self.listing.id, "rating": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # â”€â”€ Update review â”€â”€

    def test_update_review_success(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.patch(
            f"/api/v1/reviews/{self.review.id}/",
            {"rating": 4, "review": "Updated review."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating"], 4)
        self.assertEqual(response.data["review"], "Updated review.")
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.review, "Updated review.")

    def test_update_review_other_user_returns_403(self):
        self.client.force_authenticate(user=self.other_buyer)
        response = self.client.patch(
            f"/api/v1/reviews/{self.review.id}/",
            {"rating": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_review_invalid_rating_returns_400(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.patch(
            f"/api/v1/reviews/{self.review.id}/",
            {"rating": 10},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_review_unauthenticated_returns_401(self):
        response = self.client.patch(
            f"/api/v1/reviews/{self.review.id}/",
            {"rating": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # â”€â”€ Delete review â”€â”€

    def test_delete_review_success(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.delete(f"/api/v1/reviews/{self.review.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=self.review.id).exists())

    def test_delete_review_other_user_returns_403(self):
        self.client.force_authenticate(user=self.other_buyer)
        response = self.client.delete(f"/api/v1/reviews/{self.review.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Review.objects.filter(pk=self.review.id).exists())

    def test_delete_review_unauthenticated_returns_401(self):
        response = self.client.delete(f"/api/v1/reviews/{self.review.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # â”€â”€ Seller reviews â”€â”€

    def test_seller_reviews_list(self):
        response = self.client.get(f"/api/v1/sellers/{self.seller.id}/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_seller_reviews_ordered_by_newest_first(self):
        Review.objects.create(
            reviewer=self.other_buyer,
            seller=self.seller,
            listing=self.listing,
            rating=4,
            review="Good.",
        )
        response = self.client.get(f"/api/v1/sellers/{self.seller.id}/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertGreaterEqual(
            results[0]["created_at"], results[1]["created_at"]
        )

    def test_seller_reviews_nonexistent_seller_returns_404(self):
        response = self.client.get("/api/v1/sellers/99999/reviews/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # â”€â”€ Rating summary â”€â”€

    def test_seller_rating_summary(self):
        response = self.client.get(f"/api/v1/sellers/{self.seller.id}/rating-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_rating"], 5.0)
        self.assertEqual(response.data["rating_count"], 1)
        self.assertEqual(response.data["rating_distribution"]["5"], 1)

    def test_seller_rating_summary_no_reviews(self):
        response = self.client.get(f"/api/v1/sellers/{self.other_buyer.id}/rating-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_rating"], 0.0)
        self.assertEqual(response.data["rating_count"], 0)
        self.assertEqual(response.data["rating_distribution"]["5"], 0)

    def test_seller_rating_summary_distribution(self):
        Review.objects.create(
            reviewer=self.other_buyer,
            seller=self.seller,
            listing=self.listing,
            rating=4,
            review="Good.",
        )
        response = self.client.get(f"/api/v1/sellers/{self.seller.id}/rating-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating_count"], 2)
        self.assertEqual(response.data["rating_distribution"]["5"], 1)
        self.assertEqual(response.data["rating_distribution"]["4"], 1)

    # â”€â”€ List my reviews â”€â”€

    def test_list_my_reviews(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_my_reviews_returns_only_my_reviews(self):
        Review.objects.create(
            reviewer=self.other_buyer,
            seller=self.seller,
            listing=self.listing,
            rating=3,
            review="Okay.",
        )
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get("/api/v1/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.review.id)
