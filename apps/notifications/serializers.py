from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "body",
            "type",
            "reference_id",
            "reference_type",
            "is_read",
            "created_at",
        ]


class NotificationMarkReadSerializer(serializers.Serializer):
    is_read = serializers.BooleanField(default=True)


class UnreadCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
