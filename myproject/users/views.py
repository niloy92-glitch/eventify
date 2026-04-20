import requests
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_GET, require_POST

from .forms import LoginJSONForm, RegisterJSONForm
from .services import (
    AUTH_DEFAULT_ROLE,
    AUTH_MESSAGE_KEYS,
    DJANGO_ADMIN_URL,
    ROLE_LABELS,
    add_auth_notice,
    auth_context,
    build_google_auth_url,
    create_user_from_registration,
    dashboard_context,
    admin_activity_logs_data,
    admin_approvals_data,
    admin_base_context,
    admin_dashboard_data,
    admin_users_data,
    exchange_google_code_for_token,
    fetch_google_userinfo,
    google_oauth_configured,
    is_django_admin_user,
    login_redirect_url,
    normalize_role,
    role_dashboard_url,
    send_verification_email,
    verification_required,
)


User = get_user_model()


def _first_form_error(form) -> str:
    field_errors = form.errors.get_json_data()
    for errors in field_errors.values():
        if errors:
            return errors[0]["message"]
    return "Invalid form data."


# ── Page views ───────────────────────────────────────────────────────────────

@require_GET
def root_redirect(request: HttpRequest) -> HttpResponse:
    return redirect("users:login")


@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        if is_django_admin_user(request.user):
            return redirect(DJANGO_ADMIN_URL)
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
    return render(request, "users/auth.html", auth_context(request, "login"))


@require_GET
def register_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        if is_django_admin_user(request.user):
            return redirect(DJANGO_ADMIN_URL)
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
    return render(request, "users/auth.html", auth_context(request, "register"))


# ── Email verification ───────────────────────────────────────────────────────

@require_GET
def verify_email(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return render(request, "users/verification_result.html", {
            "success": False,
            "heading": "Verification Failed",
            "message": "This verification link is invalid or has expired.",
        })

    if default_token_generator.check_token(user, token):
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        return render(request, "users/verification_result.html", {
            "success": True,
            "heading": "Email Verified!",
            "message": "Your email has been successfully verified. Redirecting to login…",
            "redirect_url": add_auth_notice(
                f"{reverse('users:login')}?role={user.role}",
                AUTH_MESSAGE_KEYS["email_verified"],
            ),
        })

    return render(request, "users/verification_result.html", {
        "success": False,
        "heading": "Verification Failed",
        "message": "This verification link is invalid or has expired.",
    })


# ── Google OAuth ─────────────────────────────────────────────────────────────

@require_GET
def google_oauth_start(request: HttpRequest) -> HttpResponse:
    if not google_oauth_configured():
        return redirect(add_auth_notice(
            f"{reverse('users:login')}?role={normalize_role(request.GET.get('role'))}",
            AUTH_MESSAGE_KEYS["oauth_failed"],
        ))

    role = normalize_role(request.GET.get("role"))
    mode = str(request.GET.get("mode", "login")).strip().lower()
    if mode not in {"login", "register"}:
        mode = "login"

    return redirect(build_google_auth_url(request, role, mode))


@require_GET
def google_oauth_callback(request: HttpRequest) -> HttpResponse:
    if not google_oauth_configured():
        return redirect(add_auth_notice(reverse("users:login"), AUTH_MESSAGE_KEYS["oauth_failed"]))

    state_token = request.GET.get("state", "")
    code = request.GET.get("code", "")
    error = request.GET.get("error", "")

    if error or not code:
        return redirect(add_auth_notice(reverse("users:login"), AUTH_MESSAGE_KEYS["oauth_failed"]))

    try:
        state_data = signing.loads(state_token, salt="users.google.oauth", max_age=600)
    except signing.BadSignature:
        return redirect(add_auth_notice(reverse("users:login"), AUTH_MESSAGE_KEYS["oauth_failed"]))

    role = normalize_role(state_data.get("role"))
    mode = str(state_data.get("mode", "login")).strip().lower()
    if mode not in {"login", "register"}:
        mode = "login"

    try:
        token_data = exchange_google_code_for_token(request, code)
        access_token = token_data.get("access_token", "")
        profile = fetch_google_userinfo(access_token)
    except requests.RequestException:
        return redirect(add_auth_notice(f"{reverse('users:login')}?role={role}", AUTH_MESSAGE_KEYS["oauth_failed"]))

    email = str(profile.get("email", "")).strip().lower()
    if not email:
        return redirect(add_auth_notice(f"{reverse('users:login')}?role={role}", AUTH_MESSAGE_KEYS["oauth_failed"]))

    google_email_verified = bool(profile.get("email_verified", False))
    full_name = str(profile.get("name", "")).strip()
    first_name = str(profile.get("given_name", "")).strip()
    last_name = str(profile.get("family_name", "")).strip()

    user = User.objects.filter(email__iexact=email).first()

    if user and is_django_admin_user(user):
        return redirect(add_auth_notice(f"{reverse('users:login')}?role={role}", AUTH_MESSAGE_KEYS["oauth_failed"]))

    if user is None:
        if mode != "register":
            return redirect(add_auth_notice(f"{reverse('users:login')}?role={role}", AUTH_MESSAGE_KEYS["oauth_failed"]))

        create_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "email_verified": google_email_verified or not verification_required(),
        }
        if role == "vendor":
            create_fields["company_name"] = full_name

        user = User.objects.create_user(
            email=email,
            password=None,
            role=role,
            **create_fields,
        )

    if verification_required() and not user.email_verified:
        if google_email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        else:
            send_verification_email(request, user)
            return redirect(add_auth_notice(
                f"{reverse('users:login')}?role={user.role}",
                AUTH_MESSAGE_KEYS["verification_required"],
            ))

    login(request, user)
    return redirect(login_redirect_url(user.role))


# ── JSON API endpoints ───────────────────────────────────────────────────────

@require_POST
def login_api(request: HttpRequest) -> JsonResponse:
    form = LoginJSONForm.from_request_body(request.body)
    if form is None:
        return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)
    if not form.is_valid():
        return JsonResponse({"ok": False, "message": _first_form_error(form)}, status=400)

    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]
    remember = form.cleaned_data.get("remember", False)
    role = form.cleaned_data["role"]
    if not User.objects.filter(email__iexact=email, role=role).exists():
        return JsonResponse({"ok": False, "message": "No user found."}, status=404)

    user = authenticate(request, username=email, password=password)
    if not user:
        return JsonResponse({"ok": False, "message": "Invalid credentials."}, status=401)
    if is_django_admin_user(user):
        return JsonResponse({"ok": False, "message": "Use Django admin for this account."}, status=403)
    if user.role != role:
        return JsonResponse({"ok": False, "message": "No user found."}, status=404)
    if verification_required() and not user.email_verified:
        return JsonResponse(
            {"ok": False, "message": "Please verify your email first. Check your inbox."},
            status=403,
        )

    login(request, user)
    request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)

    return JsonResponse(
        {
            "ok": True,
            "message": "Login successful.",
            "redirect_url": login_redirect_url(user.role),
        }
    )


@require_POST
def register_api(request: HttpRequest) -> JsonResponse:
    form = RegisterJSONForm.from_request_body(request.body)
    if form is None:
        return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)
    if not form.is_valid():
        error_message = _first_form_error(form)
        status_code = 403 if "referral" in error_message.lower() else 400
        return JsonResponse({"ok": False, "message": error_message}, status=status_code)

    role = form.cleaned_data["role"]
    user = create_user_from_registration(form.cleaned_data, verification_required())

    if verification_required():
        send_verification_email(request, user)
        return JsonResponse(
            {
                "ok": True,
                "message": f"{ROLE_LABELS[role]} registration successful. Please verify your email.",
                "redirect_url": add_auth_notice(
                    f"{reverse('users:login')}?role={role}",
                    AUTH_MESSAGE_KEYS["verification_required"],
                ),
            }
        )

    login(request, user)
    return JsonResponse(
        {
            "ok": True,
            "message": f"{ROLE_LABELS[role]} registration successful.",
            "redirect_url": login_redirect_url(role),
        }
    )


# ── Dashboard & Logout ───────────────────────────────────────────────────────

@login_required(login_url="users:login")
@require_GET
def dashboard(request: HttpRequest, role: str) -> HttpResponse:
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)

    current_role = normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE))
    if role != current_role:
        return redirect(role_dashboard_url(current_role))

    if role == "admin":
        return redirect("users:admin_dashboard")

    return render(request, f"users/dashboard_{role}.html", dashboard_context(request, role))


@login_required(login_url="users:login")
@require_GET
def admin_dashboard_view(request: HttpRequest) -> HttpResponse:
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    context = admin_base_context(request, "dashboard")
    context.update(admin_dashboard_data())
    return render(request, "users/dashboard_admin.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_users_view(request: HttpRequest) -> HttpResponse:
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    context = admin_base_context(request, "users")
    context.update(admin_users_data())
    return render(request, "users/admin_users.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_approvals_view(request: HttpRequest) -> HttpResponse:
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    context = admin_base_context(request, "approvals")
    context.update(admin_approvals_data())
    return render(request, "users/admin_approvals.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_activity_logs_view(request: HttpRequest) -> HttpResponse:
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    page_number = request.GET.get("page", "1")
    context = admin_base_context(request, "activity_logs")
    context.update(admin_activity_logs_data(page_number=page_number))
    return render(request, "users/admin_activity_logs.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_profile_view(request: HttpRequest) -> HttpResponse:
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    context = admin_base_context(request, "")
    context.update(
        {
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "phone": request.user.phone or "Not provided",
            "address": request.user.address or "Not provided",
            "join_date": request.user.date_joined,
        }
    )
    return render(request, "users/admin_profile.html", context)


@require_POST
def logout_view(request: HttpRequest) -> JsonResponse:
    logout(request)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Logged out."})
    return redirect("users:login")
