import requests
from urllib.parse import urlencode

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_GET, require_POST

from users.forms import AdminUserForm, LoginForm, RegisterForm
from users.models import ApprovalStatusChoices
from users.services import (
    AUTH_DEFAULT_ROLE,
    AUTH_MESSAGE_KEYS,
    DJANGO_ADMIN_URL,
    add_auth_notice,
    auth_context,
    admin_activity_logs_data,
    admin_approvals_data,
    admin_base_context,
    admin_dashboard_data,
    admin_users_data,
    build_google_auth_url,
    client_base_context,
    client_dashboard_data,
    create_user_from_registration,
    dashboard_context,
    exchange_google_code_for_token,
    fetch_google_userinfo,
    google_oauth_configured,
    is_django_admin_user,
    login_redirect_url,
    normalize_role,
    role_dashboard_url,
    send_verification_email,
    vendor_base_context,
    vendor_dashboard_data,
    verification_required,
)


User = get_user_model()
VERIFICATION_REQUIRED_MESSAGE = "Please verify your email first. Check your inbox."


def _first_form_error(form) -> str:
    field_errors = form.errors.get_json_data()
    for errors in field_errors.values():
        if errors:
            return errors[0]["message"]
    return "Invalid form data."


def _bool_from_post(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _resend_verification_url(email: str, role: str) -> str | None:
    safe_email = str(email or "").strip().lower()
    if not safe_email:
        return None
    query = urlencode({"email": safe_email, "role": normalize_role(role)})
    return f"{reverse('users:resend_verification_email')}?{query}"


def _auth_form_values_from_post(post_data: dict) -> dict:
    return {
        "login_email": str(post_data.get("email", "")).strip(),
        "login_remember": _bool_from_post(post_data.get("remember")),
        "client_first_name": str(post_data.get("client_first_name", "")).strip(),
        "client_last_name": str(post_data.get("client_last_name", "")).strip(),
        "client_email": str(post_data.get("client_email", "")).strip(),
        "vendor_company_name": str(post_data.get("vendor_company_name", "")).strip(),
        "vendor_email": str(post_data.get("vendor_email", "")).strip(),
        "admin_first_name": str(post_data.get("admin_first_name", "")).strip(),
        "admin_last_name": str(post_data.get("admin_last_name", "")).strip(),
        "admin_email": str(post_data.get("admin_email", "")).strip(),
        "admin_referral_code": str(post_data.get("admin_referral_code", "")).strip(),
    }


def _admin_access_redirect(request: HttpRequest):
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
    return None


def _vendor_access_redirect(request: HttpRequest):
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "vendor":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
    return None


# ── Page views ───────────────────────────────────────────────────────────────

@require_GET
def root_redirect(request: HttpRequest) -> HttpResponse:
    return redirect("users:login")


def login_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        if is_django_admin_user(request.user):
            return redirect(DJANGO_ADMIN_URL)
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    active_role = normalize_role(request.POST.get("role") if request.method == "POST" else request.GET.get("role"))
    if request.method == "GET":
        context = auth_context(request, "login", active_role=active_role)
        notice_message = str(request.GET.get("auth_message", "")).strip()
        if notice_message:
            context.update(
                {
                    "status_message": notice_message,
                    "status_level": str(request.GET.get("auth_level", "info")).strip() or "info",
                }
            )
            if notice_message == VERIFICATION_REQUIRED_MESSAGE:
                resend_url = _resend_verification_url(request.GET.get("email", ""), active_role)
                if resend_url:
                    context["resend_verification_url"] = resend_url
        return render(request, "auth.html", context)

    form = LoginForm.from_post_data(request.POST, active_role)
    if not form.is_valid():
        context = auth_context(
            request,
            "login",
            active_role=active_role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update({"status_message": _first_form_error(form), "status_level": "error"})
        return render(request, "auth.html", context, status=400)

    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]
    remember = form.cleaned_data.get("remember", False)
    role = form.cleaned_data["role"]

    if not User.objects.filter(email__iexact=email, role=role).exists():
        context = auth_context(
            request,
            "login",
            active_role=role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update({"status_message": "No user found.", "status_level": "error"})
        return render(request, "auth.html", context, status=404)

    user = authenticate(request, username=email, password=password)
    if not user:
        context = auth_context(
            request,
            "login",
            active_role=role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update({"status_message": "Invalid credentials.", "status_level": "error"})
        return render(request, "auth.html", context, status=401)
    if is_django_admin_user(user):
        context = auth_context(
            request,
            "login",
            active_role=role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update({"status_message": "Use Django admin for this account.", "status_level": "error"})
        return render(request, "auth.html", context, status=403)
    if user.role != role:
        context = auth_context(
            request,
            "login",
            active_role=role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update({"status_message": "No user found.", "status_level": "error"})
        return render(request, "auth.html", context, status=404)
    if verification_required() and not user.email_verified:
        context = auth_context(
            request,
            "login",
            active_role=role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update(
            {
                "status_message": VERIFICATION_REQUIRED_MESSAGE,
                "status_level": "error",
            }
        )
        resend_url = _resend_verification_url(email, role)
        if resend_url:
            context["resend_verification_url"] = resend_url
        return render(request, "auth.html", context, status=403)

    login(request, user)
    request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)
    return redirect(login_redirect_url(user.role))


def register_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        if is_django_admin_user(request.user):
            return redirect(DJANGO_ADMIN_URL)
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))

    active_role = normalize_role(request.POST.get("role") if request.method == "POST" else request.GET.get("role"))
    if request.method == "GET":
        return render(request, "auth.html", auth_context(request, "register", active_role=active_role))

    form = RegisterForm.from_post_data(request.POST, active_role)
    if not form.is_valid():
        error_message = _first_form_error(form)
        context = auth_context(
            request,
            "register",
            active_role=active_role,
            form_values=_auth_form_values_from_post(request.POST),
        )
        context.update({"status_message": error_message, "status_level": "error"})
        status_code = 403 if "referral" in error_message.lower() else 400
        return render(request, "auth.html", context, status=status_code)

    role = form.cleaned_data["role"]
    user = create_user_from_registration(form.cleaned_data, verification_required())

    if verification_required():
        send_verification_email(request, user)
        return redirect(
            add_auth_notice(
                f"{reverse('users:login')}?{urlencode({'role': role, 'email': user.email})}",
                AUTH_MESSAGE_KEYS["verification_required"],
            )
        )

    login(request, user)
    return redirect(login_redirect_url(role))


# ── Email verification ───────────────────────────────────────────────────────

@require_GET
def verify_email(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return render(request, "verification_result.html", {
            "success": False,
            "heading": "Verification Failed",
            "message": "This verification link is invalid or has expired.",
        })

    if default_token_generator.check_token(user, token):
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        return render(request, "verification_result.html", {
            "success": True,
            "heading": "Email Verified!",
            "message": "Your email has been successfully verified. Redirecting to login…",
            "redirect_url": add_auth_notice(
                f"{reverse('users:login')}?role={user.role}",
                AUTH_MESSAGE_KEYS["email_verified"],
            ),
        })

    return render(request, "verification_result.html", {
        "success": False,
        "heading": "Verification Failed",
        "message": "This verification link is invalid or has expired.",
    })


@require_GET
def resend_verification_email_view(request: HttpRequest) -> HttpResponse:
    role = normalize_role(request.GET.get("role"))
    email = str(request.GET.get("email", "")).strip().lower()

    if email and verification_required():
        user = User.objects.filter(email__iexact=email, email_verified=False).first()
        if user:
            send_verification_email(request, user)

    query = urlencode(
        {
            "role": role,
            "email": email,
            "auth_level": "success",
            "auth_message": "If an unverified account exists for this email, a verification link has been sent.",
        }
    )
    return redirect(f"{reverse('users:login')}?{query}")


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
            create_fields["vendor_approval_status"] = ApprovalStatusChoices.PENDING

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
                f"{reverse('users:login')}?{urlencode({'role': user.role, 'email': user.email})}",
                AUTH_MESSAGE_KEYS["verification_required"],
            ))

    login(request, user)
    return redirect(login_redirect_url(user.role))


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

    if role == "client":
        return redirect("users:client_dashboard")

    if role == "vendor":
        return redirect("users:vendor_dashboard")

    return render(request, f"users/{role}/dashboard.html", dashboard_context(request, role))


def _client_access_redirect(request: HttpRequest):
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "client":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
    return None


@login_required(login_url="users:login")
@require_GET
def client_dashboard_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = client_base_context(request, "dashboard")
    context.update(client_dashboard_data(request))
    return render(request, "users/client/dashboard.html", context)


@login_required(login_url="users:login")
@require_GET
def vendor_dashboard_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = vendor_base_context(request, "dashboard")
    context.update(vendor_dashboard_data(request))
    return render(request, "users/vendor/dashboard.html", context)



@login_required(login_url="users:login")
@require_GET
def vendor_profile_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = vendor_base_context(request, "")
    context.update(
        {
            "email": request.user.email,
            "company_name": request.user.company_name or "Not provided",
            "phone": request.user.phone or "Not provided",
            "address": request.user.address or "Not provided",
            "join_date": request.user.date_joined,
        }
    )
    return render(request, "users/vendor/profile.html", context)


@login_required(login_url="users:login")
@require_POST
def vendor_profile_update_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    company_name = str(request.POST.get("company_name", "")).strip()
    phone = str(request.POST.get("phone", "")).strip()
    address = str(request.POST.get("address", "")).strip()

    user = request.user
    user.company_name = company_name
    user.phone = phone
    user.address = address
    user.save()

    return redirect(add_auth_notice(reverse("users:vendor_profile"), AUTH_MESSAGE_KEYS["user_updated"]))


@login_required(login_url="users:login")
@require_POST
def vendor_delete_account_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    password = request.POST.get("password", "")
    user = request.user

    if not user.check_password(password):
        return redirect(add_auth_notice(reverse("users:vendor_profile"), AUTH_MESSAGE_KEYS["user_delete_failed"]))

    logout(request)
    user.delete()
    return redirect(add_auth_notice(f"{reverse('users:login')}?role=vendor", AUTH_MESSAGE_KEYS["user_deleted"]))


@login_required(login_url="users:login")
@require_GET
def client_profile_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = client_base_context(request, "")
    context.update(
        {
            "email": request.user.email,
            "first_name": request.user.first_name or "Not provided",
            "last_name": request.user.last_name or "Not provided",
            "phone": request.user.phone or "Not provided",
            "address": request.user.address or "Not provided",
            "join_date": request.user.date_joined,
        }
    )
    return render(request, "users/client/profile.html", context)


@login_required(login_url="users:login")
@require_POST
def client_profile_update_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    first_name = str(request.POST.get("first_name", "")).strip()
    last_name = str(request.POST.get("last_name", "")).strip()
    phone = str(request.POST.get("phone", "")).strip()
    address = str(request.POST.get("address", "")).strip()

    user = request.user
    user.first_name = first_name
    user.last_name = last_name
    user.phone = phone
    user.address = address
    user.save()

    return redirect(add_auth_notice(reverse("users:client_profile"), AUTH_MESSAGE_KEYS["user_updated"]))


@login_required(login_url="users:login")
@require_POST
def client_delete_account_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    password = request.POST.get("password", "")
    user = request.user

    if not user.check_password(password):
        return redirect(add_auth_notice(reverse("users:client_profile"), AUTH_MESSAGE_KEYS["user_delete_failed"]))

    logout(request)
    user.delete()
    return redirect(add_auth_notice(f"{reverse('users:login')}?role=client", AUTH_MESSAGE_KEYS["user_deleted"]))


@login_required(login_url="users:login")
@require_GET
def admin_dashboard_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = admin_base_context(request, "dashboard")
    context.update(admin_dashboard_data())
    return render(request, "users/admin/dashboard.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_users_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = admin_base_context(request, "users")
    context.update(admin_users_data())
    notice = request.GET.get("auth_message", "").strip()
    if notice:
        context["notice"] = notice
        context["notice_level"] = request.GET.get("auth_level", "info").strip() or "info"
    return render(request, "users/admin/users.html", context)


@login_required(login_url="users:login")
@require_POST
def admin_user_update_view(request: HttpRequest, user_id: int) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    requested_role = normalize_role(request.POST.get("role"))
    if requested_role in {"client", "vendor", "admin"}:
        user.role = requested_role
    form = AdminUserForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        return redirect(add_auth_notice(reverse("users:admin_users"), AUTH_MESSAGE_KEYS["user_updated"]))

    return redirect(add_auth_notice(reverse("users:admin_users"), AUTH_MESSAGE_KEYS["user_update_failed"]))


@login_required(login_url="users:login")
@require_POST
def admin_user_delete_view(request: HttpRequest, user_id: int) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    user.delete()
    return redirect(add_auth_notice(reverse("users:admin_users"), AUTH_MESSAGE_KEYS["user_deleted"]))


@login_required(login_url="users:login")
@require_GET
def admin_approvals_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = admin_base_context(request, "approvals")
    selected_filter = request.GET.get("filter", "all")
    from_date = request.GET.get("from_date", "").strip()
    to_date = request.GET.get("to_date", "").strip()
    context.update(admin_approvals_data(filter_key=selected_filter, from_date=from_date, to_date=to_date))
    return render(request, "users/admin/approvals.html", context)


@login_required(login_url="users:login")
@require_POST
def admin_approval_update_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    decision = str(request.POST.get("decision", "")).strip().lower()
    request_type = str(request.POST.get("request_type", "")).strip().lower()
    request_id = str(request.POST.get("request_id", "")).strip()

    redirect_params = {
        "filter": str(request.POST.get("filter", "all")).strip() or "all",
        "from_date": str(request.POST.get("from_date", "")).strip(),
        "to_date": str(request.POST.get("to_date", "")).strip(),
    }
    filtered_params = {key: value for key, value in redirect_params.items() if value}
    redirect_url = reverse("users:admin_approvals")
    if filtered_params:
        redirect_url = f"{redirect_url}?{urlencode(filtered_params)}"

    if decision not in {"approve", "reject"} or request_type not in {"vendor", "service"} or not request_id.isdigit():
        return redirect(add_auth_notice(redirect_url, AUTH_MESSAGE_KEYS["approval_update_failed"]))

    target_status = ApprovalStatusChoices.ALLOWED if decision == "approve" else ApprovalStatusChoices.REJECTED

    if request_type == "vendor":
        vendor = get_object_or_404(User, pk=int(request_id), role="vendor")
        vendor.vendor_approval_status = target_status
        vendor.save(update_fields=["vendor_approval_status"])
    else:
        from services.models import ApprovalRequest

        approval_request = get_object_or_404(ApprovalRequest, pk=int(request_id), request_type="service")
        approval_request.status = target_status
        approval_request.save(update_fields=["status"])

        service = approval_request.service
        service.is_approved = target_status == ApprovalStatusChoices.ALLOWED
        service.save(update_fields=["is_approved"])

    return redirect(add_auth_notice(redirect_url, AUTH_MESSAGE_KEYS["approval_updated"]))


@login_required(login_url="users:login")
@require_GET
def admin_activity_logs_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    page_number = request.GET.get("page", "1")
    context = admin_base_context(request, "activity_logs")
    context.update(admin_activity_logs_data(page_number=page_number))
    return render(request, "users/admin/activity_logs.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_profile_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

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
    return render(request, "users/admin/profile.html", context)


@require_POST
def logout_view(request: HttpRequest) -> JsonResponse:
    logout(request)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Logged out."})
    return redirect("users:login")
