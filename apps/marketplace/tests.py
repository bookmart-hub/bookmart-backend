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

    def test_create_listing_with_custom_category(self):
        """Ensure listing created with title, author, and category assigns category to newly created book."""
        self.client.force_authenticate(user=self.seller)
        url = "/api/v1/marketplace/listings/"
        data = {
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "category": "Distributed Systems",
            "price": "750.00",
            "condition": "LIKE_NEW",
            "front_cover": self.get_dummy_file("front.gif"),
            "back_cover": self.get_dummy_file("back.gif"),
            "spine": self.get_dummy_file("spine.gif"),
            "middle_page": self.get_dummy_file("middle.gif"),
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        book = Book.objects.get(title="Designing Data-Intensive Applications")
        self.assertTrue(book.categories.filter(name="Distributed Systems").exists())


class BookListingUpdateTests(APITestCase):

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

        self.dummy_image_data = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
        )

    def get_dummy_file(self, name):
        return SimpleUploadedFile(name, self.dummy_image_data, content_type="image/gif")

    def _create_listing(self, seller=None):
        seller = seller or self.seller
        listing = BookListing.objects.create(
            book=self.book,
            seller=seller,
            price=600.00,
            condition="GOOD",
            status="AVAILABLE",
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
        return listing

    def test_update_listing_success(self):
        """Ensure owner can fully update a listing."""
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "450.00",
            "condition": "LIKE_NEW",
            "condition_notes": "Excellent shape",
            "status": "SOLD",
            "latitude": "12.9716",
            "longitude": "77.5946",
        }
        response = self.client.put(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["price"], "450.00")
        self.assertEqual(response.data["condition"], "LIKE_NEW")
        self.assertEqual(response.data["condition_notes"], "Excellent shape")
        self.assertEqual(response.data["status"], "SOLD")
        self.assertEqual(response.data["latitude"], "12.971600")
        self.assertEqual(response.data["longitude"], "77.594600")

    def test_partial_update_listing_success(self):
        """Ensure owner can partially update a listing with PATCH."""
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"price": "399.00"}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["price"], "399.00")
        self.assertEqual(response.data["condition"], "GOOD")
        listing.refresh_from_db()
        self.assertEqual(listing.price, 399.00)

    def test_update_unauthenticated_returns_401(self):
        """Ensure unauthenticated request cannot update a listing."""
        listing = self._create_listing()
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        response = self.client.put(url, {"price": "100.00"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_another_users_listing_returns_403(self):
        """Ensure a user cannot edit another user's listing."""
        listing = self._create_listing(seller=self.seller)
        self.client.force_authenticate(user=self.buyer)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        response = self.client.put(url, {"price": "100.00"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_with_image_removal(self):
        """Ensure removed images are deleted from storage and DB."""
        listing = self._create_listing()
        image_ids = list(listing.listing_images.values_list("id", flat=True))
        self.assertEqual(len(image_ids), 2)

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "550.00",
            "removed_image_ids": [image_ids[0]],
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BookListingImage.objects.filter(book_listing=listing).count(), 1)
        self.assertFalse(
            BookListingImage.objects.filter(id=image_ids[0]).exists()
        )

    def test_update_with_image_replacement(self):
        """Ensure uploading a new image for a label replaces the existing one."""
        listing = self._create_listing()
        front_id = listing.listing_images.get(label="FRONT_COVER").id

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "499.00",
            "front_cover": self.get_dummy_file("new_front.gif"),
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(BookListingImage.objects.filter(book_listing=listing).count(), 2)
        self.assertFalse(
            BookListingImage.objects.filter(id=front_id).exists()
        )
        new_front = BookListingImage.objects.get(
            book_listing=listing, label="FRONT_COVER"
        )
        self.assertIn("new_front", new_front.image.name)

    def test_update_preserves_unchanged_images(self):
        """Ensure images are preserved when not explicitly replaced."""
        listing = self._create_listing()
        initial_count = listing.listing_images.count()

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"price": "499.00"}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            BookListingImage.objects.filter(book_listing=listing).count(),
            initial_count,
        )

    def test_update_negative_price_returns_400(self):
        """Ensure negative price is rejected."""
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"price": "-10.00"}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)

    def test_update_invalid_condition_returns_400(self):
        """Ensure invalid condition is rejected."""
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"condition": "MINT"}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("condition", response.data)

    def test_update_with_invalid_removed_image_ids_returns_400(self):
        """Ensure removed_image_ids from other listings are rejected."""
        listing = self._create_listing()
        other_listing = self._create_listing(seller=self.other_seller)
        other_image_id = other_listing.listing_images.first().id

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"removed_image_ids": [other_image_id]}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("removed_image_ids", response.data)

    def test_update_with_book_id(self):
        """Ensure updating book_id switches the associated book."""
        listing = self._create_listing()
        new_book = Book.objects.create(title="New Book Title")
        Author.objects.create(name="New Author").books.add(new_book)

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"book_id": new_book.id}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book"]["title"], "New Book Title")

    def test_update_with_title_and_author_creates_new_book(self):
        """Ensure providing title and author creates/finds a book and links it."""
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {"title": "Clean Code", "author": "Robert C. Martin"}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book"]["title"], "Clean Code")

    def test_update_rollback_on_invalid_data(self):
        """Ensure database rolls back when validation fails mid-operation."""
        listing = self._create_listing()
        original_price = listing.price

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "-5.00",
            "removed_image_ids": [listing.listing_images.first().id],
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        listing.refresh_from_db()
        self.assertEqual(listing.price, original_price)
        self.assertEqual(listing.listing_images.count(), 2)

    def test_patch_ignores_empty_multipart_fields(self):
        """Ensure PATCH with empty optional multipart fields updates only meaningful values."""
        listing = self._create_listing()
        original_condition = listing.condition
        original_status = listing.status

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "399.00",
            "condition": "",
            "status": "",
            "latitude": "",
            "longitude": "",
            "condition_notes": "",
            "categories": "",
            "removed_image_ids": "0",
            "book_id": "",
            "title": "",
            "author": "",
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["price"], "399.00")
        self.assertEqual(response.data["condition"], original_condition)
        self.assertEqual(response.data["status"], original_status)
        self.assertEqual(response.data["condition_notes"], "")

    def test_patch_ignores_placeholder_removed_image_ids(self):
        """Ensure PATCH ignores removed_image_ids=0 and empty string placeholders."""
        listing = self._create_listing()
        original_image_count = listing.listing_images.count()

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "499.00",
            "removed_image_ids": "0",
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["price"], "499.00")
        self.assertEqual(
            BookListingImage.objects.filter(book_listing=listing).count(),
            original_image_count,
        )

    def test_patch_ignores_empty_file_uploads(self):
        """Ensure PATCH ignores empty uploaded files and preserves existing images."""
        listing = self._create_listing()
        original_image_count = listing.listing_images.count()

        empty_file = SimpleUploadedFile("empty.gif", b"", content_type="image/gif")

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "550.00",
            "front_cover": empty_file,
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["price"], "550.00")
        self.assertEqual(
            BookListingImage.objects.filter(book_listing=listing).count(),
            original_image_count,
        )

    def test_put_still_requires_all_fields(self):
        """Ensure PUT is not affected by PATCH normalization and enforces serializer validation."""
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"

        data = {
            "price": "",
            "condition": "LIKE_NEW",
            "status": "AVAILABLE",
        }
        response = self.client.put(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)

    def test_patch_ignores_empty_price(self):
        """Ensure PATCH ignores empty price and preserves existing value."""
        listing = self._create_listing()
        original_price = listing.price

        self.client.force_authenticate(user=self.seller)
        url = f"/api/v1/marketplace/listings/{listing.id}/"
        data = {
            "price": "",
            "condition": "LIKE_NEW",
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertEqual(listing.price, original_price)
        self.assertEqual(listing.condition, "LIKE_NEW")


