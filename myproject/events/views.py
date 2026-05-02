from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import EventForm, EventPaymentForm
from .models import Event, EventServiceBooking
from services.models import Service, ServiceAvailabilitySlot
from users.services import (
	AUTH_DEFAULT_ROLE,
	AUTH_MESSAGE_KEYS,
	DJANGO_ADMIN_URL,
	add_auth_notice,
	client_base_context,
	is_django_admin_user,
	login_redirect_url,
	normalize_role,
	vendor_dashboard_data,
	vendor_base_context,
)


def _client_access_redirect(request: HttpRequest):
	if is_django_admin_user(request.user):
		return redirect(DJANGO_ADMIN_URL)
	if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "client":
		return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
	return None


def _vendor_access_redirect(request: HttpRequest):
	if is_django_admin_user(request.user):
		return redirect(DJANGO_ADMIN_URL)
	if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "vendor":
		return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
	return None


def _display_name(user) -> str:
	return user.get_full_name().strip() or user.email


def _client_event_model():
	return Event


def _booking_request_model():
	return EventServiceBooking


def _serialize_client_event(event) -> dict:
	payment_choices = dict(getattr(event, "PAYMENT_METHODS", [])) if hasattr(event, "PAYMENT_METHODS") else {}
	service_rows = []
	total_cost = Decimal("0.00")

	bookings = getattr(event, "service_requests", None)
	if bookings is not None:
		bookings = bookings.select_related("service", "service__vendor").all()
		for booking in bookings:
			price_value = booking.price_snapshot if booking.price_snapshot is not None else getattr(booking.service, "price", None)
			if price_value is not None:
				total_cost += Decimal(str(price_value))
			service_rows.append(
				{
					"id": booking.pk,
					"service_name": booking.service.name,
					"vendor_name": booking.vendor.company_name or _display_name(booking.vendor),
					"status": booking.status,
					"status_label": booking.status.title(),
					"status_badge": "pending" if booking.status == "pending" else "confirmed" if booking.status == "approved" else "rejected",
					"price": f"{Decimal(str(price_value or 0)):.2f}",
				}
			)

	return {
		"id": event.pk,
		"title": event.title,
		"event_date": event.event_date.strftime("%Y-%m-%d"),
		"event_date_label": event.event_date.strftime("%A, %B %d, %Y"),
		"venue_name": event.venue_name or "Venue not set",
		"venue_address": event.venue_address or "",
		"has_own_venue": bool(event.has_own_venue),
		"notes": event.notes or "",
		"payment_method": event.payment_method or "",
		"payment_method_label": payment_choices.get(event.payment_method, "Not selected"),
		"payment_saved_at": event.payment_saved_at.isoformat() if event.payment_saved_at else "",
		"created_at": event.created_at.isoformat() if event.created_at else "",
		"total_cost": f"{total_cost:.2f}",
		"service_count": len(service_rows),
		"service_rows": service_rows,
		"service_labels": ", ".join(row["service_name"] for row in service_rows) if service_rows else "No services booked",
	}


@login_required(login_url="users:login")
@require_GET
def client_my_events_view(request: HttpRequest) -> HttpResponse:
	redirect_response = _client_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	context = client_base_context(request, "my_events")
	event_model = _client_event_model()
	events = []
	selected_event_id = str(request.GET.get("event", "")).strip()

	if event_model is not None:
		queryset = event_model.objects.filter(client=request.user).prefetch_related("service_requests__service", "service_requests__vendor").order_by("-event_date", "-created_at")
		events = [_serialize_client_event(event) for event in queryset]

	filters = [
		{"key": "all", "label": "All", "active": True},
		{"key": "upcoming", "label": "Upcoming", "active": False},
		{"key": "completed", "label": "Completed", "active": False},
		{"key": "venue", "label": "Own venue", "active": False},
	]

	context.update(
		{
			"page_name": "My Events",
			"event_form": EventForm(),
			"payment_form": EventPaymentForm(),
			"events": events,
			"event_filters": filters,
			"selected_event_id": selected_event_id,
			"event_payload": events,
		}
	)
	return render(request, "users/client/my_events.html", context)


@login_required(login_url="users:login")
@require_GET
def client_event_detail_view(request: HttpRequest, event_id: int) -> HttpResponse:
	redirect_response = _client_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	event = get_object_or_404(
		Event.objects.prefetch_related("service_requests__service", "service_requests__vendor"),
		pk=event_id,
		client=request.user,
	)
	selected_event = _serialize_client_event(event)
	context = client_base_context(request, "my_events")
	context.update(
		{
			"page_name": "Event Details",
			"selected_event": selected_event,
			"event": selected_event,
			"event_form": EventForm(instance=event),
			"back_url": reverse("events:client_my_events"),
			"update_url": reverse("events:client_event_update", args=[event.pk]),
		}
	)
	return render(request, "users/client/event_detail.html", context)


@login_required(login_url="users:login")
@require_POST
def client_event_create_view(request: HttpRequest) -> HttpResponse:
	redirect_response = _client_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	form = EventForm(request.POST)
	if not form.is_valid():
		error_messages = [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
		error_msg = " | ".join(error_messages)
		return redirect(add_auth_notice(reverse("events:client_my_events"), f"Invalid input: {error_msg}"))

	event = form.save(commit=False)
	event.client = request.user
	event.save()
	return redirect(add_auth_notice(reverse("events:client_my_events"), AUTH_MESSAGE_KEYS["event_created"]))


@login_required(login_url="users:login")
@require_POST
def client_event_update_view(request: HttpRequest, event_id: int) -> HttpResponse:
	redirect_response = _client_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	event = get_object_or_404(Event, pk=event_id, client=request.user)
	form = EventForm(request.POST, instance=event)
	if form.is_valid():
		form.save()
		return redirect(add_auth_notice(f"{reverse('events:client_my_events')}?event={event.pk}", AUTH_MESSAGE_KEYS["event_updated"]))

	error_messages = [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
	error_msg = " | ".join(error_messages)
	return redirect(add_auth_notice(f"{reverse('events:client_my_events')}?event={event.pk}", f"Update failed: {error_msg}"))


@login_required(login_url="users:login")
@require_POST
def client_event_payment_view(request: HttpRequest, event_id: int) -> HttpResponse:
	redirect_response = _client_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	event = get_object_or_404(Event, pk=event_id, client=request.user)
	form = EventPaymentForm(request.POST)
	if form.is_valid():
		event.payment_method = form.cleaned_data["payment_method"]
		event.payment_saved_at = timezone.now()
		event.save(update_fields=["payment_method", "payment_saved_at", "updated_at"])
		return redirect(add_auth_notice(f"{reverse('events:client_my_events')}?event={event.pk}", AUTH_MESSAGE_KEYS["payment_updated"]))

	return redirect(add_auth_notice(f"{reverse('events:client_my_events')}?event={event.pk}", AUTH_MESSAGE_KEYS["payment_update_failed"]))


@login_required(login_url="users:login")
@require_POST
def client_event_delete_view(request: HttpRequest, event_id: int) -> HttpResponse:
	redirect_response = _client_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	event = get_object_or_404(Event, pk=event_id, client=request.user)
	if event.service_requests.exists():
		return redirect(add_auth_notice(f"{reverse('events:client_my_events')}?event={event.pk}", AUTH_MESSAGE_KEYS["event_delete_failed"]))

	event.delete()
	return redirect(add_auth_notice(reverse("events:client_my_events"), AUTH_MESSAGE_KEYS["event_deleted"]))


@login_required(login_url="users:login")
@require_GET
def vendor_events_view(request: HttpRequest) -> HttpResponse:
	redirect_response = _vendor_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	context = vendor_base_context(request, "events")
	
	from users.services import _serialize_booking_request
	queryset = EventServiceBooking.objects.select_related("event", "service", "service__vendor").filter(vendor=request.user, status='approved').order_by("-requested_date")
	approved_events = [_serialize_booking_request(item) for item in queryset]
	
	context.update({
		"page_name": "Events",
		"approved_events": approved_events
	})
	return render(request, "users/vendor/events.html", context)


@login_required(login_url="users:login")
@require_GET
def vendor_booking_requests_view(request: HttpRequest) -> HttpResponse:
	redirect_response = _vendor_access_redirect(request)
	if redirect_response is not None:
		return redirect_response

	context = vendor_base_context(request, "booking_requests")
	context.update(vendor_dashboard_data(request))
	context["page_name"] = "Booking Requests"
	return render(request, "users/vendor/booking_requests.html", context)


def _ensure_service_availability(service: Service, days_ahead: int = 90) -> list[str]:
	today = timezone.localdate()
	dates = []
	for offset in range(days_ahead):
		slot_date = today + timedelta(days=offset)
		ServiceAvailabilitySlot.objects.get_or_create(service=service, available_date=slot_date)
		dates.append(slot_date.strftime("%Y-%m-%d"))
	return dates


def _service_availability_dates(service: Service) -> list[str]:
	slots = list(service.availability_slots.filter(is_active=True).order_by("available_date").values_list("available_date", flat=True))
	if not slots:
		slots = [timezone.localdate() + timedelta(days=offset) for offset in range(90)]
		for slot_date in slots:
			ServiceAvailabilitySlot.objects.get_or_create(service=service, available_date=slot_date)
	return [slot.strftime("%Y-%m-%d") for slot in slots]


def _serialize_upcoming_event(event: Event) -> dict:
	return {
		"id": event.pk,
		"title": event.title,
		"event_date": event.event_date.strftime("%Y-%m-%d"),
		"event_date_label": event.event_date.strftime("A, %B %d, %Y"),
		"venue_name": event.venue_name or "Venue not set",
		"has_own_venue": bool(event.has_own_venue),
	}


def _booking_status_badge(status: str) -> str:
	if status == "approved":
		return "confirmed"
	if status == "rejected":
		return "rejected"
	return "pending"

