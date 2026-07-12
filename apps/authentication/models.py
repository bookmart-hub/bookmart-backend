import datetime

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin):
    class AuthProvider(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        GOOGLE = "GOOGLE", "Google"
        FACEBOOK = "FACEBOOK", "Facebook"
        APPLE = "APPLE", "Apple"  # Added Apple matching your UI buttons

    # Explicit mapping to match the exact fields in 01-sign-up.png
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)

    provider = models.CharField(
        max_length=20, choices=AuthProvider.choices, default=AuthProvider.EMAIL
    )
    provider_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    email_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"  # Logs in using Email string context primarily
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name


class EmailOTP(models.Model):
    """
    Handles secure validation states (Email Verify)
    and the password reset OTP.
    """

    class OTPPurpose(models.TextChoices):
        VERIFY_ACCOUNT = "VERIFY_ACCOUNT", "Account Verification"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset Authorization"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    # Matches the 4-digit input screen
    code = models.CharField(max_length=4, db_index=True)
    purpose = models.CharField(max_length=30, choices=OTPPurpose.choices)
    is_used = models.BooleanField(default=False)

    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # OTP tokens expire strictly 5 minutes after initialization
            self.expires_at = timezone.now() + datetime.timedelta(minutes=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purpose} code for {self.user.email}"
