from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Author, Book
from apps.marketplace.models import BookListing, BookListingImage

User = get_user_model()


class BookListingTests(APITestCase):

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

        self.author = Author.objects.create(name="Thomas H. Corman")
        self.book = Book.objects.create(title="Introduction to Algorithm")
        self.book.authors.add(self.author)

        # 1x1 transparent pixel GIF
        self.dummy_image_data = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
        )

    def get_dummy_file(self, name):
        return SimpleUploadedFile(name, self.dummy_image_data, content_type="image/gif")

    def test_create_listing_unauthenticated(self):
        """Ensure unauthenticated request fails to create a listing."""
        url = "/api/v1/marketplace/listings/"
        data = {
            "book_id": self.book.id,
            "price": "999.00",
            "condition": "GOOD",
            "condition_notes": "No tattered pages",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_listing_with_existing_book_id(self):
        """Ensure listing is created with pre-existing catalog book ID and all required images."""
        self.client.force_authenticate(user=self.seller)
        url = "/api/v1/marketplace/listings/"
        data = {
            "book_id": self.book.id,
            "price": "500.00",
            "condition": "LIKE_NEW",
            "condition_notes": "Almost new condition",
            "latitude": "12.9716",
            "longitude": "77.5946",
            "front_cover": self.get_dummy_file("front.gif"),
            "back_cover": self.get_dummy_file("back.gif"),
            "spine": self.get_dummy_file("spine.gif"),
            "middle_page": self.get_dummy_file("middle.gif"),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BookListing.objects.count(), 1)
        listing = BookListing.objects.first()
        self.assertEqual(listing.book, self.book)
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.price, 500.00)
        self.assertEqual(listing.condition, "LIKE_NEW")

        # Verify all 4 required listing images are created with their labels
        self.assertEqual(listing.listing_images.count(), 4)
        labels = [img.label for img in listing.listing_images.all()]
        self.assertIn("FRONT_COVER", labels)
        self.assertIn("BACK_COVER", labels)
        self.assertIn("SPINE", labels)
        self.assertIn("MIDDLE_PAGE", labels)

    def test_create_listing_missing_required_images(self):
        """Ensure listing fails validation if any required cover image is missing."""
        self.client.force_authenticate(user=self.seller)
        url = "/api/v1/marketplace/listings/"

        # Missing spine and middle_page
        data = {
            "book_id": self.book.id,
            "price": "500.00",
            "condition": "LIKE_NEW",
            "front_cover": self.get_dummy_file("front.gif"),
            "back_cover": self.get_dummy_file("back.gif"),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("spine", response.data)
        self.assertIn("middle_page", response.data)

    def test_create_listing_with_manual_entry(self):
        """Ensure manual book/author creation works along with cover uploads."""
        self.client.force_authenticate(user=self.seller)
        url = "/api/v1/marketplace/listings/"
        data = {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "price": "450.00",
            "condition": "GOOD",
            "condition_notes": "Slight highlightings",
            "front_cover": self.get_dummy_file("front.gif"),
            "back_cover": self.get_dummy_file("back.gif"),
            "spine": self.get_dummy_file("spine.gif"),
            "middle_page": self.get_dummy_file("middle.gif"),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Book.objects.filter(title="Clean Code").exists())
        book = Book.objects.get(title="Clean Code")
        self.assertTrue(book.authors.filter(name="Robert C. Martin").exists())

        listing = BookListing.objects.get(book=book)
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.price, 450.00)
        self.assertEqual(listing.listing_images.count(), 4)

    def test_get_listings_list(self):
        """Ensure get request returns listing details along with serialised images list."""
        listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=600.00,
            condition="GOOD",
            status="AVAILABLE",
        )
        BookListingImage.objects.create(
            book_listing=listing,
            image=self.get_dummy_file("front.gif"),
            label="FRONT_COVER",
        )

        self.client.force_authenticate(user=self.buyer)
        url = "/api/v1/marketplace/listings/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["book"]["title"], "Introduction to Algorithm")
        self.assertEqual(data["seller"]["full_name"], "Seller User")
        self.assertEqual(len(data["listing_images"]), 1)
        self.assertEqual(data["listing_images"][0]["label"], "FRONT_COVER")
        self.assertIsNotNone(data["listing_images"][0]["image_url"])

    def test_listing_image_upload_endpoint(self):
        """Ensure separate endpoint to upload image works."""
        self.client.force_authenticate(user=self.seller)
        listing = BookListing.objects.create(
            book=self.book,
            seller=self.seller,
            price=600.00,
            condition="GOOD",
            status="AVAILABLE",
        )

        url = "/api/v1/marketplace/listing-images/"
        data = {
            "book_listing": listing.id,
            "label": "DAMAGE_1",
            "image": self.get_dummy_file("damage1.gif"),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BookListingImage.objects.count(), 1)
        image_obj = BookListingImage.objects.first()
        self.assertEqual(image_obj.book_listing, listing)
        self.assertEqual(image_obj.label, "DAMAGE_1")
