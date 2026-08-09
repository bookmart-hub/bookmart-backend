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


class DeviceSerializer(serializers.Serializer):
    expo_push_token = serializers.CharField(max_length=255)

    def validate_expo_push_token(self, value):
        if not value or not isinstance(value, str):
            raise serializers.ValidationError("Token must be a valid non-empty string.")
        return value

