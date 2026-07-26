import logging
import threading

from django.conf import settings
from templated_mail.mail import BaseEmailMessage

from apps.authentication.models import User

logger = logging.getLogger(__name__)


# LOCAL DEVELOPMENT ONLY
# When SMTP is not configured, this service prints the OTP to the Django
# terminal instead of attempting delivery. Remove or guard this fallback
# if you do not want OTPs exposed in local logs.
def _is_smtp_configured() -> bool:
    if settings.DEBUG:
        return False
    return bool(
        getattr(settings, "EMAIL_HOST", None)
        and getattr(settings, "EMAIL_HOST_USER", None)
        and getattr(settings, "EMAIL_HOST_PASSWORD", None)
    )


class EmailNotificationService:
    @staticmethod
    def _send_email_async(email: str, template_name: str, context: dict):
        try:
            msg = BaseEmailMessage(
                template_name=template_name,
                context=context,
            )
            msg.send([email])
        except Exception as e:
            logger.error(
                f"Failed to dispatch transactional mail to {email}. Error: {str(e)}",
                exc_info=True,
            )

    @staticmethod
    def send_otp_email(user: User, otp_code: str, purpose="ACTIVATION") -> bool:
        """
        Dispatches a transactional HTML email containing the security verification OTP
        in a background thread to prevent HTTP request blocking.
        """
        if not _is_smtp_configured():
            print(
                f"\n{'=' * 50}\n"
                f"BOOKMART DEVELOPMENT OTP\n"
                f"Email : {user.email}\n"
                f"OTP   : {otp_code}\n"
                f"Expires: 10 minutes\n"
                f"{'=' * 50}\n"
            )
            return True

        subject = (
            "Verify your Bookmart Account"
            if purpose == "ACTIVATION"
            else "Reset your Bookmart Password"
        )

        context = {
            "full_name": user.full_name,
            "otp_code": otp_code,
            "subject": subject,
        }

        thread = threading.Thread(
            target=EmailNotificationService._send_email_async,
            args=(user.email, "emails/otp_notification.html", context),
            daemon=True,
        )
        thread.start()
        return True
