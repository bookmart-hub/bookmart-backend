"""
URL configuration for bookmart project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import debug_toolbar
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

admin.site.site_header = "Bookmart Admin Panel"
admin.site.site_title = "Bookmart"
admin.site.index_title = "Admin Panel"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("__debug__/", include(debug_toolbar.urls)),
    path("auth/", include("apps.authentication.urls")),
    # --- AUTOMATED API DOCUMENTATION ENDPOINTS ---
    # Generates the raw schema map payload (.yaml/.json download)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Interactive Swagger GUI: Perfect for executing live test mutations
    path(
        "docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Clean alternative ReDoc layout reader view (Clean for frontend reading)
    path(
        "docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc-ui"
    ),
]
