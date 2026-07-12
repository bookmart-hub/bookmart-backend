from django.urls import path

# from rest_framework.routers import DefaultRouter
from apps.authentication.views import auth, otp, user

# router = DefaultRouter()
# router.register("me/", user.UserViewSet)

urlpatterns = [
    path("auth/login/", auth.LoginView.as_view(), name="login"),
    path("auth/logout/", auth.LogoutView.as_view(), name="logout"),
    path("auth/register/", auth.RegisterView.as_view(), name="register"),
    path("auth/refresh/", auth.RefreshTokenView.as_view(), name="token_refresh"),
    path(
        "otp/verify-register-otp/",
        otp.VerifyOTPView.as_view(),
        name="verify-register-otp",
    ),
    # path(
    #     "otp/verify-reset-otp/",
    #     otp.VerifyResetOTPView.as_view(),
    #     name="verify-reset-otp",
    # ),
    path("user/me/", user.UserViewSet.as_view(), name="current-user"),
]  # + router.urls
