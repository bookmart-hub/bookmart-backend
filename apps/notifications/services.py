from django.db.models import Count

from apps.authentication.models import User
from apps.notifications.models import Notification


def create_notification(
    user: User,
    title: str,
    body: str,
    notification_type: str = Notification.NotificationType.SYSTEM,
    reference_id: int | None = None,
    reference_type: str | None = None,
) -> Notification:
    return Notification.objects.create(
        user=user,
        title=title,
        body=body,
        type=notification_type,
        reference_id=reference_id,
        reference_type=reference_type,
    )


def bulk_create_notifications(
    notifications_data: list[dict],
) -> list[Notification]:
    notifications = [
        Notification(
            user=data["user"],
            title=data["title"],
            body=data["body"],
            type=data.get("type", Notification.NotificationType.SYSTEM),
            reference_id=data.get("reference_id"),
            reference_type=data.get("reference_type"),
        )
        for data in notifications_data
    ]
    return Notification.objects.bulk_create(notifications)


def mark_read(notification_id: int, user: User) -> Notification | None:
    updated = Notification.objects.filter(
        pk=notification_id,
        user=user,
        is_read=False,
    ).update(is_read=True)
    if not updated:
        return None
    return Notification.objects.get(pk=notification_id)


def mark_all_read(user: User) -> int:
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True)


def unread_count(user: User) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


def get_user_notifications(user: User):
    return Notification.objects.filter(user=user).select_related("user")


def delete_notification(notification_id: int, user: User) -> bool:
    deleted, _ = Notification.objects.filter(
        pk=notification_id,
        user=user,
    ).delete()
    return deleted > 0


# Auto notification helpers


def notify_requirement_matched(requirement, listing) -> Notification | None:
    if not requirement or not listing:
        return None
    return create_notification(
        user=requirement.user,
        title="Requirement Matched",
        body=f"A new listing matches your requirement for \"{requirement.book_title}\".",
        notification_type=Notification.NotificationType.REQUIREMENT_MATCH,
        reference_id=listing.id,
        reference_type="BookListing",
    )


def notify_favorite_received(user: User, listing) -> Notification | None:
    if not user or not listing:
        return None
    return create_notification(
        user=listing.seller,
        title="New Favorite",
        body=f"{user.full_name} favorited your listing \"{listing.book.title}\".",
        notification_type=Notification.NotificationType.NEW_FAVORITE,
        reference_id=listing.id,
        reference_type="BookListing",
    )


def notify_report_resolved(report) -> Notification | None:
    if not report:
        return None
    return create_notification(
        user=report.reporter,
        title="Report Resolved",
        body=f"Your report has been reviewed and resolved.",
        notification_type=Notification.NotificationType.REPORT_UPDATED,
        reference_id=report.id,
        reference_type="PlatformReport",
    )


def notify_listing_sold(listing) -> Notification | None:
    if not listing:
        return None
    return create_notification(
        user=listing.seller,
        title="Listing Sold",
        body=f"Your listing \"{listing.book.title}\" has been marked as sold.",
        notification_type=Notification.NotificationType.LISTING_SOLD,
        reference_id=listing.id,
        reference_type="BookListing",
    )


def notify_new_message(user: User, message_data: dict) -> Notification | None:
    if not user or not message_data:
        return None
    return create_notification(
        user=user,
        title="New Message",
        body=message_data.get("body", "You have a new message."),
        notification_type=Notification.NotificationType.NEW_MESSAGE,
        reference_id=message_data.get("message_id"),
        reference_type="Message",
    )
