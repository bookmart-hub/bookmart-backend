from ninja.security import HttpBearer
from apps.authentication.utils import decode_token
from apps.authentication.models import User


class JWTAuth(HttpBearer):
    def authenticate(self, request, token: str):
        payload = decode_token(token, expected_type="access")
        if not payload:
            return None

        try:
            # Attach the user instance directly onto the route context
            return User.objects.get(id=payload["user_id"], is_active=True)
        except User.DoesNotExist:
            return None
