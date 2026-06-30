from django.urls import include, path

urlpatterns = [
    # Core Djoser endpoints for /users/, /users/me/, /users/reset_password/
    path('', include('djoser.urls')),
    # JWT authentication bridges (/token/login/, /token/refresh/)
    path('jwt/', include('djoser.urls.jwt')),
]
