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


@require_GET
def root_redirect(request: HttpRequest) -> HttpResponse:
	return redirect("users:login")


@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
	if request.user.is_authenticated:
		return redirect(ROLE_REDIRECTS.get(getattr(request.user, "role", "client"), "/"))
	return render(request, "users/login.html")


@require_POST
def login_api(request: HttpRequest) -> JsonResponse:
	try:
		data = json.loads(request.body.decode("utf-8"))
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)

	email = str(data.get("email", "")).strip().lower()
	password = str(data.get("password", ""))
	remember = bool(data.get("remember", False))

	if not email or not password:
		return JsonResponse({"ok": False, "message": "Email and password are required."}, status=400)

	user = authenticate(request, username=email, password=password)
	if not user:
		return JsonResponse({"ok": False, "message": "Invalid credentials."}, status=401)

	login(request, user)
	request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)

	return JsonResponse(
		{
			"ok": True,
			"message": "Login successful.",
			"redirect_url": ROLE_REDIRECTS[user.role],
		}
	)


@login_required(login_url="users:login")
@require_GET
def dashboard(request: HttpRequest, role: str) -> HttpResponse:
	current_role = getattr(request.user, "role", None)
	if role != current_role:
		return redirect(ROLE_REDIRECTS.get(current_role, "users:login"))

	role_meta = {
		"client": {
			"title": "Client Dashboard",
			"subtitle": "Plan events, review vendors, and track requests.",
			"initials": "CL",
			"notification_title": "Client Alerts",
			"notification_text": "New vendor proposals and booking updates appear here.",
			"nav_links": [
				{"href": ROLE_REDIRECTS["client"], "label": "Overview"},
				{"href": "#summary", "label": "Summary"},
				{"href": "#activity", "label": "Activity"},
			],
		},
		"vendor": {
			"title": "Vendor Dashboard",
			"subtitle": "Manage services, inquiries, and event bookings.",
			"initials": "VD",
			"notification_title": "Vendor Alerts",
			"notification_text": "Review client leads and upcoming service requests.",
			"nav_links": [
				{"href": ROLE_REDIRECTS["vendor"], "label": "Overview"},
				{"href": "#services", "label": "Services"},
				{"href": "#activity", "label": "Activity"},
			],
		},
		"admin": {
			"title": "Admin Dashboard",
			"subtitle": "Review users, vendors, approvals, and platform activity.",
			"initials": "AD",
			"notification_title": "Admin Alerts",
			"notification_text": "Monitor system usage and moderate platform activity.",
			"nav_links": [
				{"href": ROLE_REDIRECTS["admin"], "label": "Dashboard"},
				{"href": "/admin/", "label": "Django Admin"},
				{"href": "#summary", "label": "Summary"},
				{"href": "#activity", "label": "Activity"},
			],
		},
	}

	context = role_meta[role]
	context["dashboard_url"] = ROLE_REDIRECTS[role]
	for index, link in enumerate(context["nav_links"]):
		link["active"] = index == 0
	context.update(
		{
			"role": role,
			"user_name": request.user.get_full_name().strip() or request.user.email,
			"email": request.user.email,
		}
	)
	return render(request, f"users/dashboard_{role}.html", context)


@require_POST
def logout_view(request: HttpRequest) -> JsonResponse:
	logout(request)
	if request.headers.get("x-requested-with") == "XMLHttpRequest":
		return JsonResponse({"ok": True, "message": "Logged out."})
	return redirect("users:login")
