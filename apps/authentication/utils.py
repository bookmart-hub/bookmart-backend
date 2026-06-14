from datetime import datetime, timedelta, timezone
import jwt
from django.conf import settings
from apps.authentication.models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60         # 1 Hour
REFRESH_TOKEN_EXPIRE_DAYS = 7            # 7 Days


def create_token(user_id: int, expires_delta: timedelta, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "user_id": user_id,
        "exp": expire,
        "type": token_type
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def generate_auth_tokens(user: User) -> dict:
    access_token = create_token(
        user_id=user.id,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access"
    )
    refresh_token = create_token(
        user_id=user.id,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh"
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def decode_token(token: str, expected_type: str = "access"):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.PyJWTError:
        return None
