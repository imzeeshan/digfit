import os

from gunicorn.glogging import Logger

PORT = os.getenv("PORT", "8000")
DISPLAY_HOST = os.getenv("GUNICORN_DISPLAY_HOST", "127.0.0.1")

bind = f"0.0.0.0:{PORT}"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
wsgi_app = "core.wsgi:application"


class FriendlyLogger(Logger):
    """Show a browser-friendly URL while binding on 0.0.0.0 for Docker."""

    def info(self, msg, *args, **kwargs):
        if msg in ("Listening at: %s", "Listening at: %s (%s)"):
            url = f"http://{DISPLAY_HOST}:{PORT}"
            if msg == "Listening at: %s (%s)":
                super().info("Listening at: %s (%s)", url, args[-1])
            else:
                super().info("Listening at: %s", url)
            return
        super().info(msg, *args, **kwargs)


logger_class = FriendlyLogger
