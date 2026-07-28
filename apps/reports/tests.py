from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.books.models import Author, Book
from apps.marketplace.models import BookListing
from apps.reports.models import Report

User = get_user_model()


class ReportModelTests(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            email="reporter@example.com",
            full_name="Reporter User",
            password="testpass123",
        )
        self.target_user = User.objects.create_user(
            email="target@example.com",
            full_name="Target User",
            password="testpass123",
        )
        self.author = Author.objects.create(name="Test Author")
        self.book = Book.objects.create(title="Test Book")
        self.book.authors.add(self.author)
        self.listing = BookListing.objects.create(
            book=self.book,
            seller=self.target_user,
            price=Decimal("100.00"),
            condition="GOOD",
            status="AVAILABLE",
        )

    def test_create_user_report(self):
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="HARASSMENT",
            details="Abusive messages",
        )
        self.assertEqual(report.status, "PENDING")
        self.assertIsNone(report.reported_listing)
        self.assertEqual(str(report.reporter), "Reporter User")

    def test_create_listing_report(self):
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="LISTING",
            reported_listing=self.listing,
            reason="SCAM",
            details="Fake listing",
        )
        self.assertEqual(report.status, "PENDING")
        self.assertIsNone(report.reported_user)


class ReportAPITests(APITestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            email="reporter@example.com",
            full_name="Reporter User",
            password="testpass123",
        )
        self.target_user = User.objects.create_user(
            email="target@example.com",
            full_name="Target User",
            password="testpass123",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            full_name="Admin User",
            password="adminpass123",
        )
        self.author = Author.objects.create(name="Test Author")
        self.book = Book.objects.create(title="Test Book")
        self.book.authors.add(self.author)
        self.listing = BookListing.objects.create(
            book=self.book,
            seller=self.target_user,
            price=Decimal("100.00"),
            condition="GOOD",
            status="AVAILABLE",
        )

    def _create_report(self, client, data):
        return client.post("/api/v1/reports/", data, format="json")

    # ── Anonymous users ──
    def test_anonymous_cannot_create_report(self):
        response = self._create_report(
            self.client,
            {
                "report_type": "USER",
                "reported_user": self.target_user.id,
                "reason": "ABUSE",
                "details": "Bad behavior",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Cannot report yourself ──
    def test_cannot_report_self(self):
        self.client.force_authenticate(user=self.reporter)
        response = self._create_report(
            self.client,
            {
                "report_type": "USER",
                "reported_user": self.reporter.id,
                "reason": "ABUSE",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reported_user", response.data)

    # ── Cannot report own listing ──
    def test_cannot_report_own_listing(self):
        own_listing = BookListing.objects.create(
            book=self.book,
            seller=self.reporter,
            price=Decimal("50.00"),
            condition="GOOD",
            status="AVAILABLE",
        )
        self.client.force_authenticate(user=self.reporter)
        response = self._create_report(
            self.client,
            {
                "report_type": "LISTING",
                "reported_listing": own_listing.id,
                "reason": "SCAM",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reported_listing", response.data)

    # ── Cannot duplicate report (same user) ──
    def test_cannot_duplicate_user_report(self):
        self.client.force_authenticate(user=self.reporter)
        response1 = self._create_report(
            self.client,
            {
                "report_type": "USER",
                "reported_user": self.target_user.id,
                "reason": "HARASSMENT",
                "details": "First report",
            },
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self._create_report(
            self.client,
            {
                "report_type": "USER",
                "reported_user": self.target_user.id,
                "reason": "ABUSE",
                "details": "Second report",
            },
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reported_user", response2.data)

    # ── Cannot duplicate report (same listing) ──
    def test_cannot_duplicate_listing_report(self):
        self.client.force_authenticate(user=self.reporter)
        response1 = self._create_report(
            self.client,
            {
                "report_type": "LISTING",
                "reported_listing": self.listing.id,
                "reason": "SCAM",
                "details": "First report",
            },
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self._create_report(
            self.client,
            {
                "report_type": "LISTING",
                "reported_listing": self.listing.id,
                "reason": "FAKE_LISTING",
                "details": "Second report",
            },
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reported_listing", response2.data)

    # ── Invalid reason rejected ──
    def test_invalid_reason_rejected(self):
        self.client.force_authenticate(user=self.reporter)
        response = self._create_report(
            self.client,
            {
                "report_type": "USER",
                "reported_user": self.target_user.id,
                "reason": "INVALID_REASON",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", response.data)

    # ── Valid report creation (USER) ──
    def test_create_user_report_success(self):
        self.client.force_authenticate(user=self.reporter)
        response = self._create_report(
            self.client,
            {
                "report_type": "USER",
                "reported_user": self.target_user.id,
                "reason": "HARASSMENT",
                "details": "Sending abusive DMs",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["report_type"], "USER")
        self.assertEqual(response.data["reason"], "HARASSMENT")
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["reporter"]["id"], self.reporter.id)
        self.assertEqual(response.data["reported_user"]["id"], self.target_user.id)

    # ── Valid report creation (LISTING) ──
    def test_create_listing_report_success(self):
        self.client.force_authenticate(user=self.reporter)
        response = self._create_report(
            self.client,
            {
                "report_type": "LISTING",
                "reported_listing": self.listing.id,
                "reason": "SCAM",
                "details": "Seller asked for payment outside platform",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["report_type"], "LISTING")
        self.assertEqual(response.data["reason"], "SCAM")
        self.assertEqual(response.data["reported_listing"]["id"], self.listing.id)
        # Verify enriched listing response includes book and seller
        self.assertIn("book", response.data["reported_listing"])
        self.assertIn("seller", response.data["reported_listing"])

    # ── List my reports (paginated) ──
    def test_list_my_reports(self):
        self.client.force_authenticate(user=self.reporter)
        Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
        )
        response = self.client.get("/api/v1/reports/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Paginated response
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["reason"], "ABUSE")

    # ── Pagination works on my-reports ──
    def test_my_reports_pagination(self):
        self.client.force_authenticate(user=self.reporter)
        for i in range(5):
            Report.objects.create(
                reporter=self.reporter,
                report_type="USER",
                reported_user=self.target_user,
                reason="ABUSE",
                details=f"Report {i}",
            )
        response = self.client.get("/api/v1/reports/me/?page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    # ── Normal user cannot GET /reports/ (admin-only) ──
    def test_normal_user_cannot_list_all_reports(self):
        self.client.force_authenticate(user=self.reporter)
        response = self.client.get("/api/v1/reports/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Admin can list all reports ──
    def test_admin_can_list_all_reports(self):
        self.client.force_authenticate(user=self.admin_user)
        Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
        )
        response = self.client.get("/api/v1/reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    # ── Admin can get report detail ──
    def test_admin_can_get_report_detail(self):
        self.client.force_authenticate(user=self.admin_user)
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="LISTING",
            reported_listing=self.listing,
            reason="SCAM",
        )
        response = self.client.get(f"/api/v1/reports/{report.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], report.id)
        self.assertEqual(response.data["reason"], "SCAM")

    # ── Admin can review (patch) a report ──
    def test_admin_can_review_report(self):
        self.client.force_authenticate(user=self.admin_user)
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="LISTING",
            reported_listing=self.listing,
            reason="SCAM",
        )
        response = self.client.patch(
            f"/api/v1/reports/{report.id}/",
            {"status": "RESOLVED", "review_notes": "Investigated. No issue found."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "RESOLVED")
        self.assertEqual(
            response.data["review_notes"], "Investigated. No issue found."
        )

    # ── Normal user cannot patch reports ──
    def test_normal_user_cannot_patch_report(self):
        self.client.force_authenticate(user=self.reporter)
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
        )
        response = self.client.patch(
            f"/api/v1/reports/{report.id}/",
            {"status": "RESOLVED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Invalid status rejected ──
    def test_invalid_status_rejected(self):
        self.client.force_authenticate(user=self.admin_user)
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
        )
        response = self.client.patch(
            f"/api/v1/reports/{report.id}/",
            {"status": "INVALID_STATUS"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    # ── Admin cannot modify original report content ──
    def test_admin_cannot_modify_original_content(self):
        self.client.force_authenticate(user=self.admin_user)
        report = Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
            details="Original details",
        )
        response = self.client.patch(
            f"/api/v1/reports/{report.id}/",
            {"status": "RESOLVED", "reason": "HARASSMENT"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.reason, "ABUSE")  # unchanged
        self.assertEqual(report.details, "Original details")  # unchanged
        self.assertEqual(report.status, "RESOLVED")  # updated

    # ── Admin list filtering works ──
    def test_admin_list_filters(self):
        self.client.force_authenticate(user=self.admin_user)
        Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
            status="PENDING",
        )
        Report.objects.create(
            reporter=self.reporter,
            report_type="LISTING",
            reported_listing=self.listing,
            reason="SCAM",
            status="RESOLVED",
        )
        # Filter by status
        response = self.client.get("/api/v1/reports/?status=RESOLVED")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["reason"], "SCAM")

        # Filter by report_type
        response = self.client.get("/api/v1/reports/?report_type=USER")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["reason"], "ABUSE")

        # Filter by reason
        response = self.client.get("/api/v1/reports/?reason=SCAM")
        self.assertEqual(len(response.data["results"]), 1)

    # ── Admin list search works ──
    def test_admin_list_search(self):
        self.client.force_authenticate(user=self.admin_user)
        Report.objects.create(
            reporter=self.reporter,
            report_type="USER",
            reported_user=self.target_user,
            reason="ABUSE",
        )
        # Search by reporter name
        response = self.client.get("/api/v1/reports/?search=Reporter")
        self.assertEqual(len(response.data["results"]), 1)

        # Search by reporter email
        response = self.client.get("/api/v1/reports/?search=reporter@example.com")
        self.assertEqual(len(response.data["results"]), 1)

