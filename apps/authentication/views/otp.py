from drf_spectacular.utils import extend_schema
from rest_framework import permissions, response, status, views
from rest_framework_simplejwt import tokens

from apps.authentication import serializers, services
from apps.authentication.models import EmailOTP, User


class VerifyResetOTPView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):

        # verify otp

        # set new password

        # issue JWT

        return response.Response(...)


class VerifyOTPView(views.APIView):
    queryset = EmailOTP.objects.all()
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.OTPSerializer

    @extend_schema(
        summary="Verify Registration OTP",
        description="Verify the registration OTP and activate the user account.",
        tags=["OTP Verification"],
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        otp = serializer.validated_data.get("otp")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return response.Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Execute transaction validation match rule
        if services.OTPService.verify_otp(user, otp, purpose="ACTIVATION"):
            user.email_verified = True
            user.is_active = True  # Unlock account state completely
            user.save()

            # Auto-generate dynamic tokens for immediate seamless frontend transition login dashboard entry
            refresh = tokens.RefreshToken.for_user(user)
            return response.Response(
                {
                    "detail": "Email verified successfully.",
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                },
                status=status.HTTP_200_OK,
            )

        return response.Response(
            {"detail": "Invalid or expired OTP token."},
            status=status.HTTP_400_BAD_REQUEST,
        )
