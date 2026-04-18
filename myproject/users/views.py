import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST


User = get_user_model()


ROLE_REDIRECTS = {
	"client": "/users/dashboard/client/",
	"vendor": "/users/dashboard/vendor/",
	"admin": "/users/dashboard/admin/",
}

LOGIN_REDIRECTS = {
	"client": "/client/",
	"vendor": "/vendor/",
	"admin": "/users/dashboard/admin/",
}

ROLE_LABELS = {
	"client": "Client",
	"vendor": "Vendor",
	"admin": "Admin",
}

AUTH_DEFAULT_ROLE = "client"
ADMIN_REFERRAL_CODE = "eventify"
DJANGO_ADMIN_URL = "/admin/"


def _normalize_role(role: str | None) -> str:
	selected_role = str(role or AUTH_DEFAULT_ROLE).strip().lower()
	if selected_role not in ROLE_REDIRECTS:
		return AUTH_DEFAULT_ROLE
	return selected_role


def _is_django_admin_user(user) -> bool:
	return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def _auth_context(request: HttpRequest, mode: str) -> dict:
	active_role = _normalize_role(request.GET.get("role"))
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


def _registration_payload(request: HttpRequest) -> dict:
	try:
		return json.loads(request.body.decode("utf-8"))
	except (json.JSONDecodeError, UnicodeDecodeError):
		return {}


def _landing_context(request: HttpRequest, role: str) -> dict:
	user_name = request.user.get_full_name().strip() or request.user.email
	return {
		"role": role,
		"role_label": ROLE_LABELS[role],
		"user_name": user_name,
		"message": f"hello {user_name}, {ROLE_LABELS[role].lower()}!",
	}


@require_GET
def root_redirect(request: HttpRequest) -> HttpResponse:
	return redirect("users:login")


@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
	if request.user.is_authenticated:
		if _is_django_admin_user(request.user):
			return redirect(DJANGO_ADMIN_URL)
		return redirect(LOGIN_REDIRECTS.get(getattr(request.user, "role", AUTH_DEFAULT_ROLE), "/"))
	return render(request, "users/auth.html", _auth_context(request, "login"))


@require_GET
def register_page(request: HttpRequest) -> HttpResponse:
	if request.user.is_authenticated:
		if _is_django_admin_user(request.user):
			return redirect(DJANGO_ADMIN_URL)
		return redirect(LOGIN_REDIRECTS.get(getattr(request.user, "role", AUTH_DEFAULT_ROLE), "/"))
	return render(request, "users/auth.html", _auth_context(request, "register"))


@require_POST
def login_api(request: HttpRequest) -> JsonResponse:
	try:
		data = json.loads(request.body.decode("utf-8"))
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)

	email = str(data.get("email", "")).strip().lower()
	password = str(data.get("password", ""))
	remember = bool(data.get("remember", False))
	role = _normalize_role(data.get("role"))

	if not email or not password:
		return JsonResponse({"ok": False, "message": "Email and password are required."}, status=400)
	if not User.objects.filter(email__iexact=email, role=role).exists():
		return JsonResponse({"ok": False, "message": "No user found."}, status=404)

	user = authenticate(request, username=email, password=password)
	if not user:
		return JsonResponse({"ok": False, "message": "Invalid credentials."}, status=401)
	if _is_django_admin_user(user):
		return JsonResponse({"ok": False, "message": "Use Django admin for this account."}, status=403)
	if user.role != role:
		return JsonResponse({"ok": False, "message": "No user found."}, status=404)

	login(request, user)
	request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)

	return JsonResponse(
		{
			"ok": True,
			"message": "Login successful.",
			"redirect_url": LOGIN_REDIRECTS[user.role],
		}
	)


@require_POST
def register_api(request: HttpRequest) -> JsonResponse:
	data = _registration_payload(request)
	role = _normalize_role(data.get("role"))
	email = str(data.get("email", "")).strip().lower()
	password = str(data.get("password", ""))
	confirm_password = str(data.get("confirm_password", ""))

	if not email or not password:
		return JsonResponse({"ok": False, "message": "Email and password are required."}, status=400)
	if password != confirm_password:
		return JsonResponse({"ok": False, "message": "Passwords do not match."}, status=400)
	if User.objects.filter(email__iexact=email).exists():
		return JsonResponse({"ok": False, "message": "An account with that email already exists."}, status=400)

	first_name = str(data.get("first_name", "")).strip()
	last_name = str(data.get("last_name", "")).strip()
	company_name = str(data.get("company_name", "")).strip()
	referral_code = str(data.get("referral_code", ADMIN_REFERRAL_CODE)).strip() or ADMIN_REFERRAL_CODE

	extra_fields = {
		"first_name": "",
		"last_name": "",
		"company_name": "",
		"referral_code": "",
		"is_staff": False,
		"is_active": True,
	}

	if role == "client":
		if not first_name or not last_name:
			return JsonResponse({"ok": False, "message": "First name and last name are required."}, status=400)
		extra_fields.update({"first_name": first_name, "last_name": last_name})
	elif role == "vendor":
		if not company_name:
			return JsonResponse({"ok": False, "message": "Company name is required."}, status=400)
		extra_fields.update({"company_name": company_name})
	elif role == "admin":
		if not first_name or not last_name:
			return JsonResponse({"ok": False, "message": "First name and last name are required."}, status=400)
		if referral_code.lower() != ADMIN_REFERRAL_CODE:
			return JsonResponse({"ok": False, "message": "Invalid referral code."}, status=403)
		extra_fields.update({"first_name": first_name, "last_name": last_name, "referral_code": ADMIN_REFERRAL_CODE})
	else:
		return JsonResponse({"ok": False, "message": "Invalid role selected."}, status=400)

	user = User.objects.create_user(
		email=email,
		password=password,
		role=role,
		**extra_fields,
	)

	login(request, user)
	return JsonResponse(
		{
			"ok": True,
			"message": f"{ROLE_LABELS[role]} registration successful.",
			"redirect_url": LOGIN_REDIRECTS[role],
		}
	)


@login_required(login_url="users:login")
@require_GET
def dashboard(request: HttpRequest, role: str) -> HttpResponse:
	if _is_django_admin_user(request.user):
		return redirect(DJANGO_ADMIN_URL)

	current_role = _normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE))
	if role != current_role:
		return redirect(ROLE_REDIRECTS.get(current_role, "users:login"))
	return render(request, "users/landing.html", _landing_context(request, role))


@require_POST
def logout_view(request: HttpRequest) -> JsonResponse:
	logout(request)
	if request.headers.get("x-requested-with") == "XMLHttpRequest":
		return JsonResponse({"ok": True, "message": "Logged out."})
	return redirect("users:login")
