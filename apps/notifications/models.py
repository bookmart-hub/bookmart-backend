from django.conf import settings
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_MESSAGE = "NEW_MESSAGE", "New Message"
        NEW_MATCH = "NEW_MATCH", "New Match"
        NEW_FAVORITE = "NEW_FAVORITE", "New Favorite"
        LISTING_SOLD = "LISTING_SOLD", "Listing Sold"
        REPORT_UPDATED = "REPORT_UPDATED", "Report Updated"
        REQUIREMENT_MATCH = "REQUIREMENT_MATCH", "Requirement Match"
        SYSTEM = "SYSTEM", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_notifications",
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    reference_id = models.IntegerField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} - {self.title} for {self.user.email}"
