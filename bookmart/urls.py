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

from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views.health import HealthCheckView

admin.site.site_header = "Bookmart Admin Panel"
admin.site.site_title = "Bookmart"
admin.site.index_title = "Admin Panel"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="root-health-check"),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/v1/", include("apps.authentication.urls")),
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/book/", include("apps.books.urls")),
    path("api/v1/marketplace/", include("apps.marketplace.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.requirements.urls")),
    path("api/v1/", include("apps.favorites.urls")),
    path("api/v1/", include("apps.home_feed.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.tags.urls")),
    path("docs/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc-ui",
    ),
]


if settings.DEBUG:
    urlpatterns += debug_toolbar_urls()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
