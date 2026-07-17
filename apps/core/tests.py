from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ProfileTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            full_name="Original Name",
            password="testpassword123",
        )
        self.profile = self.user.profile
        self.profile.date_of_birth = date(2000, 1, 1)
        self.profile.save()

    def test_retrieve_profile(self):
        """Ensure retrieve profile me endpoint returns correct fields."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["full_name"], "Original Name")
        self.assertEqual(response.data["date_of_birth"], "2000-01-01")
        self.assertNotIn("personalization_fields", response.data)

    def test_update_profile(self):
        """Ensure updating full_name and date_of_birth updates User and Profile models."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        data = {
            "full_name": "Updated Name",
            "date_of_birth": "1995-12-31",
            "bio": "New Bio info",
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["full_name"], "Updated Name")
        self.assertEqual(response.data["date_of_birth"], "1995-12-31")

        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.profile.date_of_birth, date(1995, 12, 31))
        self.assertEqual(self.profile.bio, "New Bio info")
