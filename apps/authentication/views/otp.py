from drf_spectacular.utils import extend_schema
from rest_framework import permissions, response, status, views
from rest_framework_simplejwt import tokens

from apps.authentication import serializers, services
from apps.authentication.models import EmailOTP, User


class VerifyResetOTPView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ResetPasswordSerializer

    @extend_schema(
        summary="Verify Reset OTP & Set Password",
        description="Verify the password reset OTP code, update the user's password, and issue login JWT keys.",
        tags=["OTP Verification"],
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        otp = serializer.validated_data.get("otp")
        new_password = serializer.validated_data.get("new_password")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return response.Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if services.OTPService.verify_otp(user, otp, purpose="PASSWORD_RESET"):
            user.set_password(new_password)
            user.email_verified = True
            user.is_active = True
            user.save()

            refresh = tokens.RefreshToken.for_user(user)
            return response.Response(
                {
                    "detail": "Password has been reset successfully.",
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
