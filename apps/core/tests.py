from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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

        # 1x1 transparent pixel GIF
        self.dummy_image_data = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
        )

    def test_retrieve_profile(self):
        """Ensure retrieve profile me endpoint returns correct fields."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["full_name"], "Original Name")
        self.assertEqual(response.data["date_of_birth"], "2000-01-01")
        self.assertNotIn("personalization_fields", response.data)
        self.assertNotIn("latitude", response.data)
        self.assertNotIn("longitude", response.data)

    def test_update_profile(self):
        """Ensure updating full_name, date_of_birth, and city_location updates User and Profile models."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        data = {
            "full_name": "Updated Name",
            "date_of_birth": "1995-12-31",
            "bio": "New Bio info",
            "city_location": "Bangalore",
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["full_name"], "Updated Name")
        self.assertEqual(response.data["date_of_birth"], "1995-12-31")
        self.assertEqual(response.data["city_location"], "Bangalore")
        self.assertNotIn("latitude", response.data)
        self.assertNotIn("longitude", response.data)

        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.profile.date_of_birth, date(1995, 12, 31))
        self.assertEqual(self.profile.bio, "New Bio info")
        self.assertEqual(self.profile.city_location, "Bangalore")

    def test_update_profile_image_valid(self):
        """Ensure updating profile with a valid image uploads the file successfully."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        image_file = SimpleUploadedFile(
            "avatar.gif", self.dummy_image_data, content_type="image/gif"
        )
        data = {"image": image_file, "bio": "Uploaded an avatar!"}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.image.name.startswith("profile/images/avatar"))
        self.assertIsNotNone(response.data["image"])

    def test_update_profile_image_invalid_type(self):
        """Ensure non-image files are rejected."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        text_file = SimpleUploadedFile(
            "doc.txt", b"plain text", content_type="text/plain"
        )
        data = {"image": text_file}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)

    def test_update_profile_image_oversized(self):
        """Ensure oversized images (exceeding 5 MB) are rejected."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/core/profile/me/"
        oversized_data = b"0" * (5 * 1024 * 1024 + 10)
        oversized_file = SimpleUploadedFile(
            "huge.gif", oversized_data, content_type="image/gif"
        )
        data = {"image": oversized_file}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)


class HealthCheckTests(APITestCase):
    def test_root_health_check(self):
        """Ensure root /health/ endpoint returns healthy status."""
        url = "/health/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertIn("services", response.data)
        self.assertEqual(response.data["services"]["database"]["status"], "up")
        self.assertEqual(response.data["services"]["storage"]["status"], "up")

    def test_api_health_check(self):
        """Ensure /api/v1/core/health endpoint returns healthy status."""
        url = "/api/v1/core/health"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
