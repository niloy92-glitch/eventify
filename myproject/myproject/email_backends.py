"""Custom email backends for production services."""

from __future__ import annotations

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import strip_tags


class ResendEmailBackend(BaseEmailBackend):
    """Send email via Resend HTTP API."""

    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages) -> int:
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            if self.fail_silently:
                return 0
            raise RuntimeError("RESEND_API_KEY is not configured.")

        sent_count = 0
        timeout = getattr(settings, "EMAIL_TIMEOUT", 10)

        for message in email_messages:
            try:
                sent = self._send_message(message, api_key, timeout)
            except Exception:
                if not self.fail_silently:
                    raise
                sent = False
            if sent:
                sent_count += 1
        return sent_count

    def _send_message(self, message, api_key: str, timeout: int) -> bool:
        from_email = (
            message.from_email
            or getattr(settings, "RESEND_FROM_EMAIL", "")
            or settings.DEFAULT_FROM_EMAIL
        )

        html_body = None
        if getattr(message, "alternatives", None):
            for body, mimetype in message.alternatives:
                if mimetype == "text/html":
                    html_body = body
                    break

        if html_body is None and getattr(message, "content_subtype", "") == "html":
            html_body = message.body

        text_body = message.body
        if html_body and not text_body:
            text_body = strip_tags(html_body)

        payload = {
            "from": from_email,
            "to": message.to or [],
            "subject": message.subject,
            "text": text_body,
        }
        if html_body:
            payload["html"] = html_body
        if message.cc:
            payload["cc"] = message.cc
        if message.bcc:
            payload["bcc"] = message.bcc
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        response = requests.post(
            self.api_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Resend API error {response.status_code}: {response.text}"
            )
        return True
