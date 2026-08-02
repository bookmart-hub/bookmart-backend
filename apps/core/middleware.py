import os
import json
import logging
from datetime import datetime
from django.conf import settings

# Setup file logging
LOG_DIR = os.path.join(settings.BASE_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "request_response.log")

logger = logging.getLogger("django.request_response")
logger.setLevel(logging.INFO)
logger.propagate = False

# Ensure file handler is added
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)


class RequestResponseLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.DEBUG:
            return self.get_response(request)

        # Pre-process request info
        method = request.method
        path = request.get_full_path()
        content_type = request.META.get("CONTENT_TYPE", "")
        
        # Read body safely without breaking django post data parsing
        body_summary = ""
        if "multipart/form-data" in content_type:
            body_summary = f"[Multipart Data: {list(request.POST.keys())} files: {list(request.FILES.keys())}]"
        elif "application/json" in content_type:
            try:
                # request.body is a bytes object
                body_bytes = request.body
                if body_bytes:
                    body_summary = body_bytes.decode("utf-8", errors="replace")[:1000]
            except Exception:
                body_summary = "[Unable to read JSON body]"
        else:
            try:
                # Other formats
                body_bytes = request.body
                if body_bytes:
                    body_summary = body_bytes.decode("utf-8", errors="replace")[:500]
            except Exception:
                pass

        log_msg = f"REQUEST: {method} {path}\nContent-Type: {content_type}\nBody: {body_summary}"
        logger.info(log_msg)

        # Process response
        response = self.get_response(request)

        resp_content_type = response.get("Content-Type", "")
        status_code = response.status_code

        resp_body_summary = ""
        if "application/json" in resp_content_type and hasattr(response, "content"):
            try:
                resp_body_summary = response.content.decode("utf-8", errors="replace")[:500]
            except Exception:
                pass

        logger.info(
            f"RESPONSE for {method} {path}:\nStatus: {status_code}\nContent-Type: {resp_content_type}\nBody: {resp_body_summary}\n"
            + "-" * 80
        )

        return response
