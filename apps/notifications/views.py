from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
)
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.notifications.serializers import (
    NotificationMarkReadSerializer,
    NotificationSerializer,
    UnreadCountSerializer,
)
from apps.notifications.services import (
    delete_notification,
    get_user_notifications,
    mark_all_read,
    mark_read,
    unread_count,
)


class NotificationListView(views.APIView):
    """GET /api/v1/notifications/ - List notifications (newest first, paginated)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List my notifications",
        description="Returns a paginated list of the authenticated user's notifications, ordered by newest first.",
        responses={200: NotificationSerializer(many=True)},
        tags=["Notifications"],
    )
    def get(self, request, *args, **kwargs):
        qs = get_user_notifications(request.user)
        from apps.marketplace.pagination import NearbyListingPagination
        paginator = NearbyListingPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = NotificationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = NotificationSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkReadView(views.APIView):
    """PATCH /api/v1/notifications/{id}/read/ - Mark one notification read"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Mark notification as read",
        description="Marks a single notification as read for the authenticated user.",
        request=NotificationMarkReadSerializer,
        responses={200: NotificationSerializer},
        tags=["Notifications"],
        examples=[
            OpenApiExample(
                "Mark read",
                summary="Mark a notification as read",
                value={"is_read": True},
                request_only=True,
            ),
        ],
    )
    def patch(self, request, pk, *args, **kwargs):
        notification = mark_read(notification_id=pk, user=request.user)
        if notification is None:
            return Response(
                {"detail": "Notification not found or already read."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(views.APIView):
    """PATCH /api/v1/notifications/read-all/ - Mark all notifications read"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        description="Marks all unread notifications as read for the authenticated user.",
        request=None,
        responses={200: OpenApiTypes.OBJECT},
        tags=["Notifications"],
        examples=[
            OpenApiExample(
                "Mark all read",
                summary="Mark all notifications as read",
                value={"detail": "All notifications marked as read."},
                response_only=True,
            ),
        ],
    )
    def patch(self, request, *args, **kwargs):
        count = mark_all_read(request.user)
        return Response(
            {"detail": f"{count} notifications marked as read."},
            status=status.HTTP_200_OK,
        )


class NotificationUnreadCountView(views.APIView):
    """GET /api/v1/notifications/unread-count/ - Get unread count"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        description="Returns the number of unread notifications for the authenticated user.",
        responses={200: UnreadCountSerializer},
        tags=["Notifications"],
        examples=[
            OpenApiExample(
                "Unread count",
                summary="Unread notification count",
                value={"count": 5},
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        count = unread_count(request.user)
        serializer = UnreadCountSerializer({"count": count})
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationDeleteView(views.APIView):
    """DELETE /api/v1/notifications/{id}/ - Delete one notification"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Delete a notification",
        description="Permanently deletes a notification belonging to the authenticated user.",
        responses={
            204: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Notifications"],
    )
    def delete(self, request, pk, *args, **kwargs):
        deleted = delete_notification(notification_id=pk, user=request.user)
        if not deleted:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


from apps.notifications.serializers import DeviceSerializer
from apps.notifications.models import Device

class DeviceRegisterView(views.APIView):
    """POST /api/v1/notifications/devices/ - Register or update a user device for push notifications"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceSerializer

    @extend_schema(
        summary="Register user device push token",
        description="Associates the authenticated user with an Expo push notification token.",
        request=DeviceSerializer,
        responses={201: OpenApiTypes.OBJECT, 200: OpenApiTypes.OBJECT},
        tags=["Notifications"],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["expo_push_token"]

        # Ensure the token belongs uniquely to this user (delete it if linked to another user previously)
        Device.objects.filter(expo_push_token=token).exclude(user=request.user).delete()
        device, created = Device.objects.get_or_create(
            user=request.user,
            expo_push_token=token,
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        detail_msg = "Device push token registered." if created else "Device push token already registered."
        return Response({"detail": detail_msg}, status=status_code)

