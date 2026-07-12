from rest_framework import permissions, views

from apps.authentication import serializers
from apps.authentication.models import User


class UserViewSet(views.APIView):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UserResponseSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return serializers.UserUpdateSerializer
        return serializers.UserResponseSerializer
