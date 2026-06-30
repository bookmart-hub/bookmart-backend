import datetime

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class AuthProvider(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        GOOGLE = "GOOGLE", "Google"
        FACEBOOK = "FACEBOOK", "Facebook"
        APPLE = "APPLE", "Apple"  # Added Apple matching your UI buttons

    # Explicit mapping to match the exact fields in 01-sign-up.png
    username = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)

    provider = models.CharField(
        max_length=20, choices=AuthProvider.choices, default=AuthProvider.EMAIL
    )
    provider_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    email_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"  # Logs in using Email string context primarily
    # Required during superuser generation commands
    REQUIRED_FIELDS = ["username"]


class EmailOTP(models.Model):
    """
    Handles secure validation states for screen 02 (Email Verify)
    and the missing password reset OTP screen.
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


class College(models.Model):
    name = models.CharField(max_length=255)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [["name", "district", "state"]]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=15, blank=True, null=True, help_text="Format: +91XXXXXXXXXX"
    )
    college = models.ForeignKey(
        College,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    # Added layout attributes to match screen 21 parameters exactly
    department_stream = models.CharField(
        max_length=150, blank=True, help_text="e.g., B.Sc, Computer Science"
    )
    city_location = models.CharField(max_length=150, default="Kolkata, India")
    is_top_seller = models.BooleanField(default=False)

    # Coordinates for "Nearest Books" feature
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Future-proofing B2C/B2B: User type flag
    is_commercial_vendor = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.full_name
