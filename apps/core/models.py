from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.authentication.models import User


class College(models.Model):
    name = models.CharField(max_length=255)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "district", "state"], name="unique_college"
            )
        ]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_validator = RegexValidator(
        regex=r"^\+?[1-9]\d{7,14}$", message="Enter a valid phone number."
    )
    phone_number = models.CharField(
        max_length=16,
        validators=[phone_validator],
        blank=True,
        null=True,
        help_text="Format: +91XXXXXXXXXX",
    )
    college = models.ForeignKey(
        College,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    personalization_fields = models.JSONField(default=dict, blank=True)

    # Added layout attributes to match screen 21 parameters exactly
    city_location = models.CharField(max_length=150, default="Kolkata, India")

    # Coordinates for "Nearest Books" feature
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # # Future-proofing B2C/B2B: User type flag
    # is_commercial_vendor = models.BooleanField(default=False)
    # company_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.full_name}'s Profile"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
