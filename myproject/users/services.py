"""
Service-layer helpers extracted from views.py.

Keeps views thin and houses reusable business logic such as
Google OAuth plumbing, email dispatch, and role helpers.
"""

import logging
from urllib.parse import urlencode
from urllib.parse import parse_qsl
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import requests
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────────────

ROLE_ROUTE_NAMES = {
    "client": "users:dashboard",
    "vendor": "users:dashboard",
    "admin": "users:dashboard",
}

LOGIN_ROUTE_NAMES = {
    "client": "client",
    "vendor": "vendor",
    "admin": "users:dashboard",
}

ROLE_LABELS = {
    "client": "Client",
    "vendor": "Vendor",
    "admin": "Admin",
}

AUTH_DEFAULT_ROLE = "client"
ADMIN_REFERRAL_CODE = "eventify"
DJANGO_ADMIN_URL = "/admin/"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

AUTH_MESSAGE_KEYS = {
    "email_verified": "EMAIL_VERIFIED",
    "verification_required": "VERIFICATION_REQUIRED",
    "oauth_failed": "OAUTH_FAILED",
    "password_reset_done": "PASSWORD_RESET_DONE",
    "password_reset_complete": "PASSWORD_RESET_COMPLETE",
}

AUTH_MESSAGES = {
    "EMAIL_VERIFIED": ("success", "Email verified. You can sign in now."),
    "VERIFICATION_REQUIRED": ("info", "Please verify your email first. Check your inbox."),
    "OAUTH_FAILED": ("error", "Google sign in failed. Please try again."),
    "PASSWORD_RESET_DONE": ("success", "If your email exists, a reset link has been sent."),
    "PASSWORD_RESET_COMPLETE": ("success", "Password reset successful. Please sign in."),
}


# ── Role helpers ─────────────────────────────────────────────────────────────

def normalize_role(role: str | None) -> str:
    selected_role = str(role or AUTH_DEFAULT_ROLE).strip().lower()
    if selected_role not in ROLE_ROUTE_NAMES:
        return AUTH_DEFAULT_ROLE
    return selected_role


def role_dashboard_url(role: str) -> str:
    return reverse(ROLE_ROUTE_NAMES[normalize_role(role)], kwargs={"role": normalize_role(role)})


def login_redirect_url(role: str) -> str:
    normalized_role = normalize_role(role)
    route_name = LOGIN_ROUTE_NAMES[normalized_role]
    if route_name == "users:dashboard":
        return reverse(route_name, kwargs={"role": normalized_role})
    return reverse(route_name)


def add_auth_notice(url: str, message_key: str) -> str:
    level, message = AUTH_MESSAGES.get(message_key, ("info", ""))
    parts = urlsplit(url)
    query_items = dict(parse_qsl(parts.query, keep_blank_values=True))
    query_items["auth_level"] = level
    query_items["auth_message"] = message
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def is_django_admin_user(user) -> bool:
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


# ── Context builders ─────────────────────────────────────────────────────────

def auth_context(request: HttpRequest, mode: str) -> dict:
    active_role = normalize_role(request.GET.get("role"))
    return {
        "mode": mode,
        "active_role": active_role,
        "roles": [
            {"value": "client", "label": ROLE_LABELS["client"]},
            {"value": "vendor", "label": ROLE_LABELS["vendor"]},
            {"value": "admin", "label": ROLE_LABELS["admin"]},
        ],
        "role_labels": ROLE_LABELS,
        "google_label": "Continue with Google" if mode == "login" else "Sign up with Google",
    }


def dashboard_context(request: HttpRequest, role: str) -> dict:
    user_name = request.user.get_full_name().strip() or request.user.email
    return {
        "role": role,
        "user_name": user_name,
    }


# ── Feature flags ────────────────────────────────────────────────────────────

def google_oauth_configured() -> bool:
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def verification_required() -> bool:
    return bool(getattr(settings, "REQUIRE_EMAIL_VERIFICATION", True))


# ── Email helpers ────────────────────────────────────────────────────────────

def _do_send_verification_email(user, verify_url: str) -> None:
    """Send verification email and raise/log on failures."""
    brand_name = getattr(settings, "EMAIL_BRAND_NAME", "Eventify")
    html_body = render_to_string("users/email_verification.html", {
        "user": user,
        "verify_url": verify_url,
        "brand_name": brand_name,
    })
    plain_body = (
        f"Welcome to {brand_name}!\n\n"
        "Please verify your email by clicking the link below:\n"
        f"{verify_url}\n\n"
        "If you did not create this account, ignore this email."
    )
    send_mail(
        subject="Verify your Eventify email",
        message=plain_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_body,
        fail_silently=False,
    )


def send_verification_email(request: HttpRequest, user) -> None:
    """Build verification URL and send after successful DB commit."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(reverse("users:verify_email", args=[uidb64, token]))

    def _send() -> None:
        try:
            _do_send_verification_email(user, verify_url)
        except Exception:
            logger.exception("Failed to send verification email to %s", user.email)
            raise

    transaction.on_commit(_send)


def create_user_from_registration(cleaned_data: dict, require_verification: bool):
    role = normalize_role(cleaned_data["role"])
    extra_fields = {
        "first_name": "",
        "last_name": "",
        "company_name": "",
        "referral_code": "",
        "is_staff": False,
        "is_active": True,
        "email_verified": not require_verification,
    }

    if role == "client":
        extra_fields.update({
            "first_name": cleaned_data["first_name"],
            "last_name": cleaned_data["last_name"],
        })
    elif role == "vendor":
        extra_fields.update({"company_name": cleaned_data["company_name"]})
    elif role == "admin":
        extra_fields.update({
            "first_name": cleaned_data["first_name"],
            "last_name": cleaned_data["last_name"],
            "referral_code": ADMIN_REFERRAL_CODE,
        })

    user_model = getattr(settings, "AUTH_USER_MODEL", "users.EventUser")
    from django.apps import apps

    user_class = apps.get_model(user_model)
    return user_class.objects.create_user(
        email=cleaned_data["email"],
        password=cleaned_data["password"],
        role=role,
        **extra_fields,
    )


# ── Google OAuth helpers ─────────────────────────────────────────────────────

def build_google_auth_url(request: HttpRequest, role: str, mode: str) -> str:
    state = signing.dumps({"role": role, "mode": mode}, salt="users.google.oauth")
    redirect_uri = request.build_absolute_uri(reverse("users:google_oauth_callback"))
    query = urlencode(
        {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "prompt": "select_account",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def exchange_google_code_for_token(request: HttpRequest, code: str) -> dict:
    redirect_uri = request.build_absolute_uri(reverse("users:google_oauth_callback"))
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def fetch_google_userinfo(access_token: str) -> dict:
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
