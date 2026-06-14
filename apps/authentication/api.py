from ninja import Router, Schema
from ninja.errors import HttpError
from django.contrib.auth import authenticate
from apps.authentication.models import User
from apps.authentication.utils import generate_auth_tokens, decode_token
from apps.authentication.security import JWTAuth

router = Router(tags=["Authentication"])

# --- schemas ---


class RegisterIn(Schema):
    email: str
    password: str
    full_name: str


class LoginIn(Schema):
    email: str
    password: str


class RefreshIn(Schema):
    refresh_token: str


class TokenOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str


class UserOut(Schema):
    id: int
    email: str
    full_name: str
    phone_number: str | None = None

# --- routes ---


@router.post("/register", response={201: UserOut})
def register(request, data: RegisterIn):
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already registered")

    user = User.objects.create_user(
        email=data.email,
        password=data.password,
        full_name=data.full_name
    )
    return 201, user


@router.post("/login", response={200: TokenOut})
def login(request, data: LoginIn):
    user = authenticate(username=data.email, password=data.password)
    if not user:
        raise HttpError(401, "Invalid credentials")
    if not user.is_active:
        raise HttpError(403, "Account disabled")

    return 200, generate_auth_tokens(user)


@router.post("/refresh", response={200: TokenOut})
def refresh(request, data: RefreshIn):
    payload = decode_token(data.refresh_token, expected_type="refresh")
    if not payload:
        raise HttpError(401, "Invalid or expired refresh token")

    try:
        user = User.objects.get(id=payload["user_id"], is_active=True)
        return 200, generate_auth_tokens(user)
    except User.DoesNotExist:
        raise HttpError(401, "User not found")


@router.get("/me", auth=JWTAuth(), response={200: UserOut})
def get_me(request):
    """Secured route example: request.auth holds the authenticated User instance"""
    return 200, request.auth
