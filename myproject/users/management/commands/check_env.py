from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Validate environment configuration for DB, SMTP, OAuth, and sender settings."

    def _require(self, key: str, value):
        if value in (None, "", []):
            raise CommandError(f"Missing required setting: {key}")

    def handle(self, *args, **options):
        self.stdout.write("Checking environment configuration...")

        # Database connectivity
        try:
            connections["default"].cursor()
            self.stdout.write(self.style.SUCCESS("DB: ok"))
        except Exception as exc:
            raise CommandError(f"DB connection failed: {exc}") from exc

        # SMTP configuration
        self._require("EMAIL_HOST", getattr(settings, "EMAIL_HOST", ""))
        self._require("EMAIL_PORT", getattr(settings, "EMAIL_PORT", ""))
        self._require("DEFAULT_FROM_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", ""))
        self.stdout.write(self.style.SUCCESS("SMTP: basic settings ok"))

        # OAuth configuration
        self._require("GOOGLE_OAUTH_CLIENT_ID", getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", ""))
        self._require("GOOGLE_OAUTH_CLIENT_SECRET", getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", ""))
        self.stdout.write(self.style.SUCCESS("OAuth: client credentials configured"))

        # Sender branding configuration
        self._require("EMAIL_BRAND_NAME", getattr(settings, "EMAIL_BRAND_NAME", ""))
        self._require("SENDER_NAME", getattr(settings, "SENDER_NAME", ""))
        self._require("SENDER_ADDRESS", getattr(settings, "SENDER_ADDRESS", ""))
        self.stdout.write(self.style.SUCCESS("Sender: branding and sender address configured"))

        self.stdout.write(self.style.SUCCESS("Environment check passed."))
