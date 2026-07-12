import secrets
from datetime import timedelta

from django.utils import timezone

from apps.authentication.models import EmailOTP


class OTPService:
    @staticmethod
    def generate_otp(user, purpose="ACTIVATION", expiry_minutes=15) -> str:
        """
        Generates a secure 4-digit numeric OTP, invalidates old ones,
        and saves a fresh master record to the database.
        """
        # Invalidate any existing active OTPs for this purpose to prevent token stuffing
        EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).update(
            is_used=True
        )

        # Cryptographically secure 4-digit number string generation
        otp_code = "".join(str(secrets.randbelow(10)) for _ in range(4))
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

        EmailOTP.objects.create(
            user=user, code=otp_code, purpose=purpose, expires_at=expires_at
        )
        return otp_code

    @staticmethod
    def verify_otp(user, otp_code, purpose="ACTIVATION") -> bool:
        """
        Validates the token signature, checks timestamps, and consumes the OTP.
        """
        try:
            otp_record = EmailOTP.objects.get(
                user=user,
                code=otp_code,
                purpose=purpose,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            # Instantly consume the token on verification match
            otp_record.is_used = True
            otp_record.save()
            return True
        except EmailOTP.DoesNotExist:
            return False
