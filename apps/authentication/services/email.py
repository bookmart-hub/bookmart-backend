import logging
import threading

from templated_mail.mail import BaseEmailMessage

from apps.authentication.models import User

logger = logging.getLogger(__name__)


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
