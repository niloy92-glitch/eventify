"""
Service-layer helpers extracted from views.py.

Keeps views thin and houses reusable business logic such as
Google OAuth plumbing, email dispatch, and role helpers.
"""

import logging
from datetime import timedelta
from urllib.parse import urlencode
from urllib.parse import parse_qsl
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import requests
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import Count
from django.db import models
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode

from .models import ApprovalStatusChoices


logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────────────

ROLE_ROUTE_NAMES = {
    "client": "users:dashboard",
    "vendor": "users:vendor_dashboard",
    "admin": "users:dashboard",
}

LOGIN_ROUTE_NAMES = {
    "client": "client",
    "vendor": "users:vendor_dashboard",
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
    "user_updated": "USER_UPDATED",
    "user_deleted": "USER_DELETED",
    "user_update_failed": "USER_UPDATE_FAILED",
    "user_delete_failed": "USER_DELETE_FAILED",
    "approval_updated": "APPROVAL_UPDATED",
    "approval_update_failed": "APPROVAL_UPDATE_FAILED",
}

AUTH_MESSAGES = {
    "EMAIL_VERIFIED": ("success", "Email verified. You can sign in now."),
    "VERIFICATION_REQUIRED": ("info", "Please verify your email first. Check your inbox."),
    "OAUTH_FAILED": ("error", "Google sign in failed. Please try again."),
    "PASSWORD_RESET_DONE": ("success", "If your email exists, a reset link has been sent."),
    "PASSWORD_RESET_COMPLETE": ("success", "Password reset successful. Please sign in."),
    "USER_UPDATED": ("success", "User updated successfully."),
    "USER_DELETED": ("success", "User deleted successfully."),
    "USER_UPDATE_FAILED": ("error", "User update failed."),
    "USER_DELETE_FAILED": ("error", "User delete failed."),
    "APPROVAL_UPDATED": ("success", "Approval status updated successfully."),
    "APPROVAL_UPDATE_FAILED": ("error", "Approval update failed."),
}


# ── Role helpers ─────────────────────────────────────────────────────────────

def normalize_role(role: str | None) -> str:
    selected_role = str(role or AUTH_DEFAULT_ROLE).strip().lower()
    if selected_role not in ROLE_ROUTE_NAMES:
        return AUTH_DEFAULT_ROLE
    return selected_role


def role_dashboard_url(role: str) -> str:
    normalized_role = normalize_role(role)
    route_name = ROLE_ROUTE_NAMES[normalized_role]
    if route_name == "users:dashboard":
        return reverse(route_name, kwargs={"role": normalized_role})
    return reverse(route_name)


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

def auth_context(
    request: HttpRequest,
    mode: str,
    active_role: str | None = None,
    form_values: dict | None = None,
) -> dict:
    selected_role = normalize_role(active_role or request.GET.get("role"))
    default_form_values = {
        "login_email": "",
        "login_remember": False,
        "client_first_name": "",
        "client_last_name": "",
        "client_email": "",
        "vendor_company_name": "",
        "vendor_email": "",
        "admin_first_name": "",
        "admin_last_name": "",
        "admin_email": "",
        "admin_referral_code": "",
    }
    if form_values:
        default_form_values.update(form_values)

    return {
        "mode": mode,
        "active_role": selected_role,
        "roles": [
            {"value": "client", "label": ROLE_LABELS["client"]},
            {"value": "vendor", "label": ROLE_LABELS["vendor"]},
            {"value": "admin", "label": ROLE_LABELS["admin"]},
        ],
        "role_labels": ROLE_LABELS,
        "google_label": "Continue with Google" if mode == "login" else "Sign up with Google",
        "form_values": default_form_values,
    }


def dashboard_context(request: HttpRequest, role: str) -> dict:
    user_name = request.user.get_full_name().strip() or request.user.email
    return {
        "role": role,
        "user_name": user_name,
    }


def _display_name(user) -> str:
    return user.get_full_name().strip() or user.email


def _vendor_event_model():
    for model in apps.get_models():
        if model.__name__ in {"Event", "VendorEvent"}:
            return model
    return None


def _concrete_field_map(model) -> dict:
    return {
        field.name: field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False)
    }


def _vendor_event_field(fields: dict, candidates: tuple[str, ...]):
    for field_name in candidates:
        if field_name in fields:
            return field_name, fields[field_name]
    return None, None


def _vendor_event_title(event) -> str:
    for field_name in ("title", "name", "event_name", "service_name"):
        value = getattr(event, field_name, "")
        if value:
            return str(value)
    return str(event)


def _vendor_event_location(event) -> str:
    for field_name in ("location", "venue", "address", "event_location"):
        value = getattr(event, field_name, "")
        if value:
            return str(value)
    return "Venue to be confirmed"


def _vendor_event_owner_field(fields: dict) -> str | None:
    for field_name in ("vendor", "owner", "organizer", "host", "created_by", "user"):
        if field_name in fields:
            return field_name
    return None


def _serialize_vendor_event(event, date_field_name: str, date_field) -> dict:
    raw_date = getattr(event, date_field_name)
    if isinstance(date_field, models.DateTimeField):
        event_dt = timezone.localtime(raw_date) if timezone.is_aware(raw_date) else raw_date
        event_date = event_dt.date()
        date_label = event_dt.strftime("%A, %B %d, %Y")
        time_label = event_dt.strftime("%I:%M %p").lstrip("0")
    else:
        event_date = raw_date
        date_label = raw_date.strftime("%A, %B %d, %Y")
        time_label = "All day"

    days_until = (event_date - timezone.localdate()).days
    if days_until <= 0:
        timing_label = "Today"
    elif days_until == 1:
        timing_label = "In 1 day"
    else:
        timing_label = f"In {days_until} days"

    status_value = getattr(event, "status", None)
    status_label = str(status_value).replace("_", " ").title() if status_value else "Upcoming"

    return {
        "title": _vendor_event_title(event),
        "date_label": date_label,
        "time_label": time_label,
        "timing_label": timing_label,
        "location": _vendor_event_location(event),
        "status_label": status_label,
        "status_badge": "info-tag",
    }


def _dummy_vendor_event(today) -> dict:
    event_date = today + timedelta(days=4)
    return {
        "title": "Summer Showcase Setup",
        "date_label": event_date.strftime("%A, %B %d, %Y"),
        "time_label": "5:30 PM",
        "timing_label": "In 4 days",
        "location": "Grand Avenue Convention Hall",
        "status_label": "Upcoming",
        "status_badge": "info-tag",
    }


def vendor_base_context(request: HttpRequest, active_menu: str) -> dict:
    user_name = _display_name(request.user)
    initials = "".join(part[0] for part in user_name.split() if part).upper()[:2] or "VN"

    nav_links = [
        {
            "label": "Dashboard",
            "href": reverse("users:vendor_dashboard"),
            "active": active_menu == "dashboard",
        },
        {
            "label": "Services",
            "href": reverse("users:vendor_services"),
            "active": active_menu == "services",
        },
        {
            "label": "Events",
            "href": reverse("users:vendor_events"),
            "active": active_menu == "events",
        },
        {
            "label": "Messages",
            "href": reverse("users:vendor_messages"),
            "active": active_menu == "messages",
        },
    ]

    return {
        "role": "vendor",
        "user_name": user_name,
        "initials": initials,
        "vendor_nav_links": nav_links,
        "notification_items": [
            "Two event inquiries are waiting for your response.",
            "A client booked a date inside the next 7 days.",
            "Your service catalog is ready for review.",
        ],
    }


def vendor_dashboard_data(request: HttpRequest) -> dict:
    today = timezone.localdate()
    window_end = today + timedelta(days=7)
    upcoming_events = []

    model = _vendor_event_model()
    if model is not None:
        fields = _concrete_field_map(model)
        date_field_name, date_field = _vendor_event_field(
            fields,
            (
                "start_datetime",
                "start_at",
                "starts_at",
                "scheduled_for",
                "event_datetime",
                "event_date",
                "date",
                "starts_on",
            ),
        )
        owner_field_name = _vendor_event_owner_field(fields)

        if date_field_name and owner_field_name:
            queryset = model._default_manager.all()
            try:
                queryset = queryset.filter(**{owner_field_name: request.user})
            except Exception:
                try:
                    queryset = queryset.filter(**{f"{owner_field_name}_id": request.user.pk})
                except Exception:
                    queryset = None

            if queryset is not None:
                if isinstance(date_field, models.DateTimeField):
                    queryset = queryset.filter(
                        **{
                            f"{date_field_name}__date__gte": today,
                            f"{date_field_name}__date__lte": window_end,
                        }
                    )
                else:
                    queryset = queryset.filter(
                        **{
                            f"{date_field_name}__gte": today,
                            f"{date_field_name}__lte": window_end,
                        }
                    )

                queryset = queryset.order_by(date_field_name)
                upcoming_events = [
                    _serialize_vendor_event(event, date_field_name, date_field)
                    for event in queryset[:6]
                ]

    if not upcoming_events:
        upcoming_events = [_dummy_vendor_event(today)]

    upcoming_count = len(upcoming_events)
    return {
        "today_label": today.strftime("%A, %B %d, %Y"),
        "stats": {
            "services": max(3, upcoming_count + 2),
            "events": upcoming_count,
            "messages": max(2, upcoming_count + 1),
            "bookings": max(1, upcoming_count - 1 if upcoming_count > 1 else 1),
        },
        "upcoming_events": upcoming_events,
    }


APPROVAL_FILTERS = {
    "all": "All",
    "allowed": "Allowed",
    "rejected": "Rejected",
    "vendors": "Vendors",
    "services": "Services",
}


def normalize_approval_filter(filter_key: str | None) -> str:
    normalized = str(filter_key or "all").strip().lower()
    if normalized not in APPROVAL_FILTERS:
        return "all"
    return normalized


def parse_filter_date(value: str | None):
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def approval_status_badge(status: str) -> str:
    if status == ApprovalStatusChoices.ALLOWED:
        return "confirmed"
    if status == ApprovalStatusChoices.REJECTED:
        return "rejected"
    return "pending"


def _approval_filter_url(filter_key: str, from_date: str, to_date: str) -> str:
    params = {"filter": filter_key}
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    return f"{reverse('users:admin_approvals')}?{urlencode(params)}"


def admin_base_context(request: HttpRequest, active_menu: str) -> dict:
    user_name = _display_name(request.user)
    initials = "".join(part[0] for part in user_name.split() if part).upper()[:2] or "AD"

    nav_links = [
        {
            "label": "Dashboard",
            "href": reverse("users:admin_dashboard"),
            "active": active_menu == "dashboard",
        },
        {
            "label": "Users",
            "href": reverse("users:admin_users"),
            "active": active_menu == "users",
        },
        {
            "label": "Approvals",
            "href": reverse("users:admin_approvals"),
            "active": active_menu == "approvals",
        },
        {
            "label": "Activity Logs",
            "href": reverse("users:admin_activity_logs"),
            "active": active_menu == "activity_logs",
        },
    ]

    return {
        "role": "admin",
        "user_name": user_name,
        "initials": initials,
        "admin_nav_links": nav_links,
        "admin_profile_url": reverse("users:admin_profile"),
        "notification_items": [
            "Two new vendor approvals are pending.",
            "A new admin account was added.",
            "Daily dashboard snapshot is ready.",
        ],
    }


def _special_day_label(today) -> str:
    special_days = {
        (1, 1): "New Year's Day",
        (3, 8): "International Women's Day",
        (3, 26): "Independence Day",
        (12, 16): "Victory Day",
    }
    return special_days.get((today.month, today.day), "No special observance today")


def client_base_context(request: HttpRequest, active_menu: str) -> dict:
    user_name = _display_name(request.user)
    initials = "".join(part[0] for part in user_name.split() if part).upper()[:2] or "CL"

    nav_links = [
        {
            "label": "Dashboard",
            "href": reverse("users:client_dashboard"),
            "active": active_menu == "dashboard",
        },
        {
            "label": "My Events",
            "href": reverse("users:client_my_events"),
            "active": active_menu == "my_events",
        },
        {
            "label": "Messages",
            "href": reverse("users:client_messages"),
            "active": active_menu == "messages",
        },
        {
            "label": "Profile",
            "href": reverse("users:client_profile"),
            "active": active_menu == "profile",
        },
    ]

    return {
        "role": "client",
        "user_name": user_name,
        "initials": initials,
        "client_nav_links": nav_links,
        "client_profile_url": reverse("users:client_profile"),
        "notification_items": [
            "A vendor sent you a quote update.",
            "One of your events starts this week.",
            "Reminder: confirm event checklist items.",
        ],
    }


def client_dashboard_data(request: HttpRequest) -> dict:
    today = timezone.localdate()
    seed = int(getattr(request.user, "pk", 1) or 1)

    total_events = max(5, (seed % 7) + 6)
    ongoing_events = 1
    upcoming_events = max(2, total_events // 2)
    canceled_events = max(1, total_events // 6)
    completed_events = max(1, total_events - upcoming_events - ongoing_events - canceled_events)
    total_events = upcoming_events + ongoing_events + canceled_events + completed_events

    upcoming_list = []
    event_names = [
        "Annual Family Meetup",
        "Office Celebration",
        "Cultural Night",
        "Birthday Gathering",
        "Wedding Reception",
    ]
    locations = ["Dhaka Club", "Banani Hall", "Gulshan Venue", "Dhanmondi Center", "Bashundhara Hall"]

    for index in range(min(5, upcoming_events)):
        event_date = today + timedelta(days=index + 1)
        upcoming_list.append(
            {
                "name": event_names[index % len(event_names)],
                "date": event_date.strftime("%A, %B %d %Y"),
                "location": locations[index % len(locations)],
            }
        )

    return {
        "today_label": today.strftime("%A, %B %d %Y"),
        "special_day_label": _special_day_label(today),
        "stats": {
            "total": total_events,
            "upcoming": upcoming_events,
            "ongoing": ongoing_events,
            "canceled": canceled_events,
            "completed": completed_events,
        },
        "upcoming_events": upcoming_list,
    }


def admin_users_data() -> dict:
    user_model = get_user_model()
    queryset = user_model.objects.filter(is_superuser=False).order_by("-date_joined")
    total_users = queryset.count()

    role_counts = {
        row["role"]: row["count"]
        for row in queryset.values("role").annotate(count=Count("id"))
    }

    rows = []
    for user in queryset:
        rows.append(
            {
                "id": user.pk,
                "name": _display_name(user),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": user.role,
                "company_name": user.company_name or "Not provided",
                "phone": user.phone or "Not provided",
                "address": user.address or "Not provided",
                "email_verified": user.email_verified,
                "join_date": timezone.localtime(user.date_joined).strftime("%d %b %Y"),
            }
        )

    return {
        "rows": rows,
        "total": total_users,
        "clients": role_counts.get("client", 0),
        "vendors": role_counts.get("vendor", 0),
        "admins": role_counts.get("admin", 0),
    }


def admin_dashboard_data() -> dict:
    user_data = admin_users_data()
    total_users = user_data["total"]
    vendors = user_data["vendors"]
    admins = user_data["admins"]

    # Event/service stats are dummy-backed while those models are not yet present.
    services = max((vendors * 3) + (admins * 2), 12)
    events_running = max(total_users // 4, 2)
    events_upcoming = max(total_users // 3, 3)
    events_canceled = max(total_users // 10, 1)
    events_completed = max(total_users // 2, 5)

    recent_activities = [
        {
            "actor": row["name"],
            "action": f"Registered as {ROLE_LABELS.get(row['role'], 'User')}",
            "timestamp": row["join_date"],
        }
        for row in user_data["rows"][:8]
    ]

    return {
        "stats": {
            "total_users": total_users,
            "vendors": vendors,
            "admins": admins,
            "services": services,
            "events_running": events_running,
            "events_upcoming": events_upcoming,
            "events_canceled": events_canceled,
            "events_completed": events_completed,
        },
        "recent_activities": recent_activities,
    }


def admin_approvals_data(filter_key: str = "all", from_date: str = "", to_date: str = "") -> dict:
    normalized_filter = normalize_approval_filter(filter_key)
    start_date = parse_filter_date(from_date)
    end_date = parse_filter_date(to_date)

    user_model = get_user_model()
    vendors = user_model.objects.filter(role="vendor").order_by("-date_joined")

    rows = []
    for vendor in vendors:
        rows.append(
            {
                "request_type": "vendor",
                "request_id": vendor.pk,
                "vendor_name": vendor.company_name or _display_name(vendor),
                "vendor_approved": vendor.vendor_approval_status == ApprovalStatusChoices.ALLOWED,
                "service_name": "N/A",
                "service_type": "N/A",
                "status": vendor.vendor_approval_status,
                "status_label": vendor.get_vendor_approval_status_display(),
                "status_badge": approval_status_badge(vendor.vendor_approval_status),
                "created_at_dt": timezone.localtime(vendor.date_joined),
            }
        )

    filtered_rows = []
    for row in rows:
        created_date = row["created_at_dt"].date()

        if start_date and created_date < start_date:
            continue
        if end_date and created_date > end_date:
            continue

        if normalized_filter == "allowed" and row["status"] != ApprovalStatusChoices.ALLOWED:
            continue
        if normalized_filter == "rejected" and row["status"] != ApprovalStatusChoices.REJECTED:
            continue
        if normalized_filter == "vendors" and row["request_type"] != "vendor":
            continue
        if normalized_filter == "services":
            continue

        row["created_at"] = row["created_at_dt"].strftime("%d %b %Y, %I:%M %p")
        filtered_rows.append(row)

    filtered_rows.sort(key=lambda item: item["created_at_dt"], reverse=True)

    return {
        "rows": filtered_rows,
        "active_filter": normalized_filter,
        "filters": [
            {
                "key": key,
                "label": label,
                "url": _approval_filter_url(key, from_date, to_date),
                "active": key == normalized_filter,
            }
            for key, label in APPROVAL_FILTERS.items()
        ],
        "from_date": from_date,
        "to_date": to_date,
    }


def admin_activity_logs_data(page_number: int = 1, per_page: int = 12) -> dict:
    user_data = admin_users_data()["rows"]
    approval_rows = admin_approvals_data()["rows"]

    logs = []
    for row in user_data:
        logs.append(
            {
                "actor": row["name"],
                "activity": f"Created account ({ROLE_LABELS.get(row['role'], 'User')})",
                "when": row["join_date"],
            }
        )

    for row in approval_rows:
        activity = "Submitted vendor account approval request"
        logs.append(
            {
                "actor": row["vendor_name"],
                "activity": activity,
                "when": row["created_at"],
            }
        )

    paginator = Paginator(logs, per_page)
    page_obj = paginator.get_page(page_number)

    return {
        "page_obj": page_obj,
        "logs": page_obj.object_list,
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
        extra_fields.update(
            {
                "company_name": cleaned_data["company_name"],
                "vendor_approval_status": ApprovalStatusChoices.PENDING,
            }
        )
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
