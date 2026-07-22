import time
import os
import sys
import platform
import logging
from django.db import connection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)

class HealthCheckView(APIView):
    """
    Health check endpoint to monitor the status of the platform, database, and media storage.
    """
    permission_classes = [permissions.AllowAny]  # Publicly accessible for monitor pings

    @extend_schema(
        summary="Check platform health",
        description="Checks status of API server, PostgreSQL database connectivity, and media storage system.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "healthy"},
                    "environment": {"type": "string", "example": "production"},
                    "timestamp": {"type": "string", "example": "2026-07-22T19:15:30.123456Z"},
                    "services": {
                        "type": "object",
                        "properties": {
                            "database": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string", "example": "up"},
                                    "latency_ms": {"type": "number", "example": 12.34}
                                }
                            },
                            "storage": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string", "example": "up"},
                                    "provider": {"type": "string", "example": "cloudinary"}
                                }
                            }
                        }
                    },
                    "system": {
                        "type": "object",
                        "properties": {
                            "python_version": {"type": "string", "example": "3.12.3"},
                            "django_version": {"type": "string", "example": "6.0.6"},
                            "os": {"type": "string", "example": "Linux-6.1.0-18-amd64"}
                        }
                    }
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "unhealthy"},
                    "services": {"type": "object"}
                }
            }
        },
        tags=["Health"]
    )
    def get(self, request):
        health_status = "healthy"
        services = {}

        # 1. Database Check
        db_start = time.time()
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
            db_latency = round((time.time() - db_start) * 1000, 2)
            services["database"] = {
                "status": "up",
                "latency_ms": db_latency
            }
        except Exception as e:
            logger.error(f"HealthCheck: Database check failed: {str(e)}")
            health_status = "unhealthy"
            services["database"] = {
                "status": "down",
                "error": str(e)
            }

        # 2. Storage Check (dynamic provider based on settings)
        storage_provider = os.getenv("STORAGE_PROVIDER", "local").lower()
        try:
            file_name = f"healthcheck_ping_{int(time.time())}.txt"
            file_content = b"ping"
            
            # Simple write, verify exists, and delete check
            path = default_storage.save(file_name, ContentFile(file_content))
            if default_storage.exists(path):
                default_storage.delete(path)
                storage_status = "up"
            else:
                storage_status = "down"
        except Exception as e:
            logger.error(f"HealthCheck: Storage ({storage_provider}) check failed: {str(e)}")
            storage_status = "down"
            # Do not mark critical platform health as unhealthy solely on storage failure,
            # or you can choose to mark it unhealthy if upload is critical. Let's keep it healthy
            # unless database is down, but report the storage status down.
            services["storage_error"] = str(e)

        services["storage"] = {
            "status": storage_status,
            "provider": storage_provider
        }

        # 3. System Info
        import django
        system_info = {
            "python_version": sys.version.split()[0],
            "django_version": django.get_version(),
            "os": platform.platform()
        }

        response_data = {
            "status": health_status,
            "environment": os.getenv("STORAGE_PROVIDER", "production") if os.getenv("RENDER") else "development",
            "timestamp": timezone.now().isoformat(),
            "services": services,
            "system": system_info
        }

        http_status = status.HTTP_200_OK if health_status == "healthy" else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(response_data, status=http_status)
