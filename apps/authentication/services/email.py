import logging

from templated_mail.mail import BaseEmailMessage

from apps.authentication.models import User

logger = logging.getLogger(__name__)


class EmailNotificationService:
    @staticmethod
    def send_otp_email(user: User, otp_code: str, purpose="ACTIVATION") -> bool:
        """
        Dispatches a transactional HTML email containing the security verification OTP.
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

        try:
            msg = BaseEmailMessage(
                template_name="emails/otp_notification.html",
                context=context,
            )
            msg.send([user.email])
            return True
        except Exception as e:
            logger.error(
                f"Failed to dispatch transactional mail to {user.email}. Error: {str(e)}"
            )
            return False
