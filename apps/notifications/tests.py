from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification

User = get_user_model()


class NotificationAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            full_name="Test User",
            password="testpassword123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            full_name="Other User",
            password="testpassword123",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            body="This is a test notification.",
            type=Notification.NotificationType.SYSTEM,
        )
        self.read_notification = Notification.objects.create(
            user=self.user,
            title="Read Notification",
            body="This notification is read.",
            type=Notification.NotificationType.SYSTEM,
            is_read=True,
        )
        self.other_notification = Notification.objects.create(
            user=self.other_user,
            title="Other User Notification",
            body="This belongs to another user.",
            type=Notification.NotificationType.SYSTEM,
        )

    # â”€â”€ List notifications â”€â”€

    def test_list_notifications_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_notifications_unauthenticated(self):
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_notifications_ordered_by_newest_first(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertGreaterEqual(results[0]["created_at"], results[1]["created_at"])

    def test_list_notifications_returns_only_user_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertNotEqual(item["title"], "Other User Notification")

    # â”€â”€ Mark single notification read â”€â”€

    def test_mark_notification_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/v1/notifications/{self.notification.id}/read/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])

    def test_mark_notification_read_other_user_returns_404(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            f"/api/v1/notifications/{self.notification.id}/read/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_already_read_notification_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/v1/notifications/{self.read_notification.id}/read/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_notification_read_other_user_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            f"/api/v1/notifications/{self.notification.id}/read/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # â”€â”€ Mark all read â”€â”€

    def test_mark_all_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch("/api/v1/notifications/read-all/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.read_notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertTrue(self.read_notification.is_read)

    def test_mark_all_read_does_not_affect_other_user(self):
        self.client.force_authenticate(user=self.user)
        self.client.patch("/api/v1/notifications/read-all/")
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    # â”€â”€ Unread count â”€â”€

    def test_unread_count(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_unread_count_zero(self):
        self.notification.is_read = True
        self.notification.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_unread_count_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    # â”€â”€ Delete notification â”€â”€

    def test_delete_notification(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f"/api/v1/notifications/{self.notification.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Notification.objects.filter(pk=self.notification.id).exists()
        )

    def test_delete_notification_other_user_returns_404(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(
            f"/api/v1/notifications/{self.notification.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            Notification.objects.filter(pk=self.notification.id).exists()
        )

    def test_delete_nonexistent_notification_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete("/api/v1/notifications/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # â”€â”€ Pagination â”€â”€

    def test_pagination_page_size(self):
        for i in range(5):
            Notification.objects.create(
                user=self.user,
                title=f"Notification {i}",
                body="Body",
                type=Notification.NotificationType.SYSTEM,
            )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/notifications/?page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 7)

    # â”€â”€ Permissions â”€â”€

    def test_unauthenticated_mark_read_returns_401(self):
        response = self.client.patch(
            f"/api/v1/notifications/{self.notification.id}/read/",
            {"is_read": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_mark_all_read_returns_401(self):
        response = self.client.patch("/api/v1/notifications/read-all/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_unread_count_returns_401(self):
        response = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_delete_returns_401(self):
        response = self.client.delete(
            f"/api/v1/notifications/{self.notification.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
