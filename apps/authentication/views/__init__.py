from apps.authentication.views.auth import LoginView, LogoutView, RegisterView
from apps.authentication.views.otp import VerifyOTPView, VerifyResetOTPView

__all__ = [
    LoginView,
    LogoutView,
    RegisterView,
    VerifyOTPView,
    VerifyResetOTPView,
]
