from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import EmailOTP
from apps.authentication.services import OTPService

User = get_user_model()


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user_email = "testreset@example.com"
        self.user_password = "old_password_123"
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            full_name="Test Reset User",
        )
        self.user.email_verified = True
        self.user.save()

        self.forgot_url = reverse("forgot-password")
        self.verify_url = reverse("verify-reset-otp")

    def test_forgot_password_valid_email(self):
        response = self.client.post(self.forgot_url, {"email": self.user_email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

        # Verify OTP record was generated in database
        otp_exists = EmailOTP.objects.filter(
            user=self.user, purpose="PASSWORD_RESET", is_used=False
        ).exists()
        self.assertTrue(otp_exists)

    def test_forgot_password_invalid_email(self):
        response = self.client.post(self.forgot_url, {"email": "nonexistent@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_reset_otp_success(self):
        # Generate OTP code manually
        otp_code = OTPService.generate_otp(self.user, purpose="PASSWORD_RESET")

        payload = {
            "email": self.user_email,
            "otp": otp_code,
            "new_password": "new_secure_password_123",
        }
        response = self.client.post(self.verify_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])

        # Authenticate with the new password to confirm update
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new_secure_password_123"))

    def test_verify_reset_otp_invalid_code(self):
        OTPService.generate_otp(self.user, purpose="PASSWORD_RESET")

        payload = {
            "email": self.user_email,
            "otp": "9999",  # wrong code
            "new_password": "new_secure_password_123",
        }
        response = self.client.post(self.verify_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SocialAuthenticationTests(APITestCase):
    def setUp(self):
        self.social_url = reverse("social-login")
        self.email = "socialuser@example.com"
        self.provider_id = "google-oauth2-id-12345"

    def test_social_login_signup_new_user(self):
        payload = {
            "provider": "GOOGLE",
            "provider_id": self.provider_id,
            "email": self.email,
            "full_name": "Google User",
        }
        response = self.client.post(self.social_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertEqual(response.data["user"]["email"], self.email)
        self.assertEqual(response.data["user"]["provider"], "GOOGLE")

        # Verify user created in DB
        user = User.objects.get(email=self.email)
        self.assertEqual(user.provider, "GOOGLE")
        self.assertEqual(user.provider_id, self.provider_id)
        self.assertTrue(user.email_verified)

    def test_social_login_existing_user_same_provider(self):
        # Create existing social user
        user = User.objects.create(
            email=self.email,
            full_name="Google User",
            provider="GOOGLE",
            provider_id=self.provider_id,
            email_verified=True,
        )
        user.set_unusable_password()
        user.save()

        payload = {
            "provider": "GOOGLE",
            "provider_id": self.provider_id,
            "email": self.email,
        }
        response = self.client.post(self.social_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)

    def test_social_login_link_native_account(self):
        # Create normal email user
        user = User.objects.create_user(
            email=self.email,
            password="somepassword123",
            full_name="Native User",
        )
        # Not verified initially
        self.assertFalse(user.email_verified)

        payload = {
            "provider": "FACEBOOK",
            "provider_id": "fb-id-98765",
            "email": self.email,
        }
        response = self.client.post(self.social_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify account was linked and verified
        user.refresh_from_db()
        self.assertEqual(user.provider, "FACEBOOK")
        self.assertEqual(user.provider_id, "fb-id-98765")
        self.assertTrue(user.email_verified)

    def test_social_login_conflict_different_social_provider(self):
        # Create existing Google user
        user = User.objects.create(
            email=self.email,
            full_name="Google User",
            provider="GOOGLE",
            provider_id=self.provider_id,
            email_verified=True,
        )
        user.save()

        # Try logging in with FACEBOOK provider
        payload = {
            "provider": "FACEBOOK",
            "provider_id": "fb-id-98765",
            "email": self.email,
        }
        response = self.client.post(self.social_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

