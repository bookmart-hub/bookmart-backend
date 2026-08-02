from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Book
from apps.marketplace.models import BookListing
from apps.requirements.models import BookRequirement

User = get_user_model()


class BookRequirementAPITests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            full_name="Owner User",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            full_name="Other User",
            password="testpass123",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            full_name="Admin User",
            password="adminpass123",
        )

    # ── Model test ──
    def test_create_requirement_model(self):
        req = BookRequirement.objects.create(
            user=self.owner,
            book_title="Operating System Concepts",
            preferred_condition="GOOD",
            min_price=Decimal("300.00"),
            max_price=Decimal("450.00"),
            notes="Need 10th edition if possible.",
        )
        self.assertEqual(req.status, "ACTIVE")
        self.assertEqual(str(req), f"Wanted: Operating System Concepts by {self.owner.full_name}")

    # ── Anonymous cannot create ──
    def test_anonymous_cannot_create(self):
        response = self.client.post(
            "/api/v1/requirements/",
            {"book_title": "Test Book", "preferred_condition": "GOOD"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Create requirement ──
    def test_create_requirement_success(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {
                "book_title": "  Operating System Concepts  ",
                "preferred_condition": "GOOD",
                "min_price": "300.00",
                "max_price": "450.00",
                "notes": "Need 10th edition if possible.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["book_title"], "Operating System Concepts")
        self.assertEqual(response.data["preferred_condition"], "GOOD")
        self.assertEqual(response.data["min_price"], "300.00")
        self.assertEqual(response.data["max_price"], "450.00")
        self.assertEqual(response.data["notes"], "Need 10th edition if possible.")
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertEqual(response.data["user"]["id"], self.owner.id)
        self.assertEqual(response.data["user"]["full_name"], "Owner User")

    # ── Create with only required fields ──
    def test_create_requirement_minimal(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {"book_title": "Clean Code"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["book_title"], "Clean Code")
        self.assertEqual(response.data["preferred_condition"], "GOOD")
        self.assertIsNone(response.data["min_price"])
        self.assertIsNone(response.data["max_price"])

    # ── Empty title rejected ──
    def test_empty_title_rejected(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {"book_title": "   ", "preferred_condition": "GOOD"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book_title", response.data)

    # ── Invalid condition rejected ──
    def test_invalid_condition_rejected(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {"book_title": "Test", "preferred_condition": "INVALID"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("preferred_condition", response.data)

    # ── Price validation: max < min rejected ──
    def test_max_price_less_than_min_rejected(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {
                "book_title": "Test",
                "min_price": "500.00",
                "max_price": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("max_price", response.data)

    # ── Negative price rejected ──
    def test_negative_min_price_rejected(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {
                "book_title": "Test",
                "min_price": "-10.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("min_price", response.data)

    # ── Public list returns only ACTIVE ──
    def test_public_list_only_active(self):
        BookRequirement.objects.create(user=self.owner, book_title="Active Book", status="ACTIVE")
        BookRequirement.objects.create(user=self.owner, book_title="Fulfilled Book", status="FULFILLED")
        BookRequirement.objects.create(user=self.owner, book_title="Cancelled Book", status="CANCELLED")

        response = self.client.get("/api/v1/requirements/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        titles = [r["book_title"] for r in response.data["results"]]
        self.assertIn("Active Book", titles)
        self.assertNotIn("Fulfilled Book", titles)
        self.assertNotIn("Cancelled Book", titles)

    # ── Public list supports search ──
    def test_public_list_search(self):
        BookRequirement.objects.create(user=self.owner, book_title="Operating System Concepts", status="ACTIVE")
        BookRequirement.objects.create(user=self.owner, book_title="Computer Networks", status="ACTIVE")

        response = self.client.get("/api/v1/requirements/?search=Operating")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["book_title"], "Operating System Concepts")

    # ── Public list supports filtering ──
    def test_public_list_filter(self):
        BookRequirement.objects.create(user=self.owner, book_title="Book1", preferred_condition="NEW", status="ACTIVE")
        BookRequirement.objects.create(user=self.owner, book_title="Book2", preferred_condition="GOOD", status="ACTIVE")

        response = self.client.get("/api/v1/requirements/?condition=NEW")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["book_title"], "Book1")

    # ── Public list pagination ──
    def test_public_list_pagination(self):
        for i in range(5):
            BookRequirement.objects.create(user=self.owner, book_title=f"Book {i}", status="ACTIVE")

        response = self.client.get("/api/v1/requirements/?page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)
        self.assertIsNotNone(response.data["next"])

    # ── Anyone can get detail ──
    def test_anyone_can_get_detail(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="Test Book", status="ACTIVE")
        response = self.client.get(f"/api/v1/requirements/{req.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book_title"], "Test Book")

    # ── Non-owner cannot update ──
    def test_non_owner_cannot_update(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="Original", status="ACTIVE")
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            f"/api/v1/requirements/{req.id}/",
            {"book_title": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Non-owner cannot delete ──
    def test_non_owner_cannot_delete(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="Original", status="ACTIVE")
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(f"/api/v1/requirements/{req.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Owner can update ──
    def test_owner_can_update(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="Original", status="ACTIVE")
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f"/api/v1/requirements/{req.id}/",
            {
                "book_title": "Updated Title",
                "preferred_condition": "LIKE_NEW",
                "notes": "Updated notes",
                "status": "FULFILLED",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book_title"], "Updated Title")
        self.assertEqual(response.data["preferred_condition"], "LIKE_NEW")
        self.assertEqual(response.data["notes"], "Updated notes")
        self.assertEqual(response.data["status"], "FULFILLED")

    # ── Owner can delete ──
    def test_owner_can_delete(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="To Delete", status="ACTIVE")
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(f"/api/v1/requirements/{req.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BookRequirement.objects.filter(id=req.id).exists())

    # ── Admin can update any requirement ──
    def test_admin_can_update_any(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="Original", status="ACTIVE")
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            f"/api/v1/requirements/{req.id}/",
            {"status": "CANCELLED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CANCELLED")

    # ── Admin can delete any requirement ──
    def test_admin_can_delete_any(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="To Delete", status="ACTIVE")
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"/api/v1/requirements/{req.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ── GET /me/ returns only my requirements ──
    def test_my_requirements(self):
        BookRequirement.objects.create(user=self.owner, book_title="My Book", status="ACTIVE")
        BookRequirement.objects.create(user=self.other_user, book_title="Other's Book", status="ACTIVE")

        self.client.force_authenticate(user=self.owner)
        response = self.client.get("/api/v1/requirements/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        titles = [r["book_title"] for r in response.data["results"]]
        self.assertIn("My Book", titles)
        self.assertNotIn("Other's Book", titles)

    # ── Invalid status on update rejected ──
    def test_invalid_status_rejected(self):
        req = BookRequirement.objects.create(user=self.owner, book_title="Test", status="ACTIVE")
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f"/api/v1/requirements/{req.id}/",
            {"status": "INVALID_STATUS"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    # ── Anonymous can view public list ──
    def test_anonymous_can_view_list(self):
        BookRequirement.objects.create(user=self.owner, book_title="Public Book", status="ACTIVE")
        response = self.client.get("/api/v1/requirements/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    # ── Create with book_id auto-populates title ──
    def test_create_with_book_id_populates_title(self):
        book = Book.objects.create(title="Atomic Habits")
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {"book_id": book.id, "preferred_condition": "GOOD"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["book_title"], "Atomic Habits")
        self.assertEqual(response.data["book"]["id"], book.id)
        self.assertEqual(response.data["book"]["title"], "Atomic Habits")

    # ── Create with book_id and manual title keeps manual title ──
    def test_create_with_book_and_manual_title_keeps_manual(self):
        book = Book.objects.create(title="Atomic Habits")
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {
                "book_id": book.id,
                "book_title": "My Custom Title",
                "preferred_condition": "GOOD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["book_title"], "My Custom Title")
        self.assertEqual(response.data["book"]["id"], book.id)

    # ── Create requires book_id or book_title ──
    def test_create_requires_book_id_or_title(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {"preferred_condition": "GOOD"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    # ── Create with invalid book_id rejected ──
    def test_create_with_invalid_book_id_rejected(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/v1/requirements/",
            {"book_id": 99999, "preferred_condition": "GOOD"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book_id", response.data)

    # ── List includes matching_count ──
    def test_list_includes_matching_count(self):
        book = Book.objects.create(title="Atomic Habits")
        req = BookRequirement.objects.create(
            user=self.owner, book=book, book_title="Atomic Habits", status="ACTIVE"
        )
        BookListing.objects.create(
            book=book,
            seller=self.other_user,
            price=Decimal("200.00"),
            condition="GOOD",
            status="AVAILABLE",
        )

        response = self.client.get("/api/v1/requirements/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["matching_count"], 1)

    # ── Matching count zero when no listings ──
    def test_matching_count_zero_when_no_listings(self):
        book = Book.objects.create(title="Atomic Habits")
        BookRequirement.objects.create(
            user=self.owner, book=book, book_title="Atomic Habits", status="ACTIVE"
        )

        response = self.client.get("/api/v1/requirements/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["matching_count"], 0)

    # ── Nearby requires authentication ──
    def test_nearby_requires_auth(self):
        response = self.client.get("/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Nearby requires lat and lng ──
    def test_nearby_requires_lat_lng(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get("/api/v1/requirements/nearby/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Nearby returns requirements within radius ──
    def test_nearby_returns_requirements_within_radius(self):
        req1 = BookRequirement.objects.create(
            user=self.owner,
            book_title="Near Book",
            status="ACTIVE",
            latitude=Decimal("28.6139"),
            longitude=Decimal("77.2090"),
        )
        BookRequirement.objects.create(
            user=self.other_user,
            book_title="Far Book",
            status="ACTIVE",
            latitude=Decimal("19.0760"),
            longitude=Decimal("72.8777"),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        titles = [r["book_title"] for r in response.data["results"]]
        self.assertIn("Near Book", titles)
        self.assertNotIn("Far Book", titles)

    # ── Nearby includes distance_km ──
    def test_nearby_includes_distance_km(self):
        BookRequirement.objects.create(
            user=self.owner,
            book_title="Near Book",
            status="ACTIVE",
            latitude=Decimal("28.6139"),
            longitude=Decimal("77.2090"),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("distance_km", response.data["results"][0])
        self.assertEqual(response.data["results"][0]["distance_km"], 0.0)

    # ── Nearby ordering by distance ──
    def test_nearby_ordering_by_distance(self):
        req_near = BookRequirement.objects.create(
            user=self.owner,
            book_title="Near Book",
            status="ACTIVE",
            latitude=Decimal("28.6140"),
            longitude=Decimal("77.2091"),
        )
        req_far = BookRequirement.objects.create(
            user=self.other_user,
            book_title="Far Book",
            status="ACTIVE",
            latitude=Decimal("28.6200"),
            longitude=Decimal("77.2100"),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50&ordering=distance"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["book_title"], "Near Book")
        self.assertEqual(results[1]["book_title"], "Far Book")

    # ── Nearby search filter ──
    def test_nearby_search_filter(self):
        BookRequirement.objects.create(
            user=self.owner,
            book_title="Atomic Habits",
            status="ACTIVE",
            latitude=Decimal("28.6139"),
            longitude=Decimal("77.2090"),
        )
        BookRequirement.objects.create(
            user=self.other_user,
            book_title="Deep Work",
            status="ACTIVE",
            latitude=Decimal("28.6140"),
            longitude=Decimal("77.2091"),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50&search=Atomic"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["book_title"] for r in response.data["results"]]
        self.assertIn("Atomic Habits", titles)
        self.assertNotIn("Deep Work", titles)

    # ── Nearby condition filter ──
    def test_nearby_condition_filter(self):
        BookRequirement.objects.create(
            user=self.owner,
            book_title="New Book",
            preferred_condition="NEW",
            status="ACTIVE",
            latitude=Decimal("28.6139"),
            longitude=Decimal("77.2090"),
        )
        BookRequirement.objects.create(
            user=self.other_user,
            book_title="Good Book",
            preferred_condition="GOOD",
            status="ACTIVE",
            latitude=Decimal("28.6140"),
            longitude=Decimal("77.2091"),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50&condition=NEW"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["book_title"] for r in response.data["results"]]
        self.assertIn("New Book", titles)
        self.assertNotIn("Good Book", titles)

    # ── Nearby price filter ──
    def test_nearby_price_filter(self):
        BookRequirement.objects.create(
            user=self.owner,
            book_title="Expensive Book",
            min_price=Decimal("500.00"),
            max_price=Decimal("1000.00"),
            status="ACTIVE",
            latitude=Decimal("28.6139"),
            longitude=Decimal("77.2090"),
        )
        BookRequirement.objects.create(
            user=self.other_user,
            book_title="Cheap Book",
            min_price=Decimal("100.00"),
            max_price=Decimal("200.00"),
            status="ACTIVE",
            latitude=Decimal("28.6140"),
            longitude=Decimal("77.2091"),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50&min_price=400"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["book_title"] for r in response.data["results"]]
        self.assertIn("Expensive Book", titles)
        self.assertNotIn("Cheap Book", titles)

    # ── Nearby pagination ──
    def test_nearby_pagination(self):
        for i in range(5):
            BookRequirement.objects.create(
                user=self.owner if i % 2 == 0 else self.other_user,
                book_title=f"Book {i}",
                status="ACTIVE",
                latitude=Decimal("28.6139"),
                longitude=Decimal("77.2090"),
            )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            "/api/v1/requirements/nearby/?lat=28.6139&lng=77.2090&radius=50&page_size=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)
        self.assertIsNotNone(response.data["next"])

    # ── Update with book_id changes book and title ──
    def test_update_with_book_id(self):
        old_book = Book.objects.create(title="Old Title")
        new_book = Book.objects.create(title="New Title")
        req = BookRequirement.objects.create(
            user=self.owner, book=old_book, book_title="Old Title", status="ACTIVE"
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f"/api/v1/requirements/{req.id}/",
            {"book_id": new_book.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book"]["id"], new_book.id)
        self.assertEqual(response.data["book"]["title"], "New Title")
        self.assertEqual(response.data["book_title"], "New Title")

    # ── Detail includes matching_count ──
    def test_detail_includes_matching_count(self):
        book = Book.objects.create(title="Atomic Habits")
        req = BookRequirement.objects.create(
            user=self.owner, book=book, book_title="Atomic Habits", status="ACTIVE"
        )
        BookListing.objects.create(
            book=book,
            seller=self.other_user,
            price=Decimal("200.00"),
            condition="GOOD",
            status="AVAILABLE",
        )

        response = self.client.get(f"/api/v1/requirements/{req.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matching_count"], 1)
        self.assertEqual(response.data["book"]["id"], book.id)
