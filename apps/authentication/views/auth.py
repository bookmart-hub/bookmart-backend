from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, response, status, views
from rest_framework_simplejwt import exceptions, tokens
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from apps.authentication import serializers, services


def get_tokens_for_user(user):
    """Helper macro to generate token packages seamlessly."""
    refresh = tokens.RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.UserRegisterSerializer

    @extend_schema(
        summary="Register User",
        description="Register a user and send verification OTP to email.",
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = serializers.UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        otp_code = services.OTPService.generate_otp(user, purpose="ACTIVATION")
        services.EmailNotificationService.send_otp_email(
            user, otp_code, purpose="ACTIVATION"
        )

        return response.Response(
            {
                "detail": "User registered successfully. 4-digit OTP code sent to your email."
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.UserLoginSerializer

    @extend_schema(
        summary="Login User",
        description="Logs in a user and returns an authentication token.",
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = serializers.UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            return response.Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.email_verified:
            return response.Response(
                {"detail": "Please verify your email address before logging in."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return response.Response(
            {
                "user": serializers.UserResponseSerializer(user).data,
                "tokens": get_tokens_for_user(user),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Logout User",
        description="Logs out a user and removes the authentication token.",
        tags=["Authentication"],
    )
    def post(self, request):
        try:
            # Safely blacklists incoming token variables to ensure a secure session closeout
            refresh_token = request.data.get("refresh")
            token = tokens.RefreshToken(refresh_token)
            token.blacklist()
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        except (exceptions.TokenError, AttributeError):
            return response.Response(
                {"detail": "Invalid or missing refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RefreshTokenView(views.APIView):
    authentication_classes = []
    serializer_class = TokenRefreshSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Refresh Access Token",
        description="Generates a new access token using a valid refresh token.",
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return response.Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):

        # send otp

        return response.Response(...)
