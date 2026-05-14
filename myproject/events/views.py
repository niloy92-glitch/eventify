from datetime import timedelta
from decimal import Decimal
import json
from urllib.parse import urlencode

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
    notify_user,
    vendor_dashboard_data,
    vendor_base_context,
)


def _client_access_redirect(request: HttpRequest):
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if (
        normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE))
        != "client"
    ):
        return redirect(
            login_redirect_url(
                getattr(request.user, "role", AUTH_DEFAULT_ROLE)
            )
        )
    return None


def _vendor_access_redirect(request: HttpRequest):
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if (
        normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE))
        != "vendor"
    ):
        return redirect(
            login_redirect_url(
                getattr(request.user, "role", AUTH_DEFAULT_ROLE)
            )
        )
    return None


def _display_name(user) -> str:
    return user.get_full_name().strip() or user.email


def _client_event_model():
    return Event


def _booking_request_model():
    return EventServiceBooking


def _serialize_client_event(event) -> dict:
    payment_choices = (
        dict(getattr(event, "PAYMENT_METHODS", []))
        if hasattr(event, "PAYMENT_METHODS")
        else {}
    )
    service_rows = []
    total_cost = Decimal("0.00")

    bookings = getattr(event, "service_requests", None)
    if bookings is not None:
        bookings = bookings.select_related("service", "service__vendor").all()
        for booking in bookings:
            price_value = booking.price_snapshot
            if booking.status == "quoted" and booking.quoted_price is not None:
                price_value = booking.quoted_price
            if price_value is None:
                price_value = getattr(booking.service, "price", None)
            if price_value is not None:
                total_cost += Decimal(str(price_value))
            service_rows.append(
                {
                    "id": booking.pk,
                    "service_name": booking.service.name,
                    "vendor_name": booking.vendor.company_name
                    or _display_name(booking.vendor),
                    "status": booking.status,
                    "status_label": (
                        "Quoted" if booking.status == "quoted" else booking.status.title()
                    ),
                    "status_badge": (
                        "pending"
                        if booking.status == "pending"
                        else "info-tag"
                        if booking.status == "quoted"
                        else (
                            "confirmed"
                            if booking.status == "approved"
                            else "rejected"
                        )
                    ),
                    "quote_note": booking.quote_note or "",
                    "quoted_price": (
                        f"{Decimal(str(booking.quoted_price)):.2f}"
                        if booking.quoted_price is not None
                        else ""
                    ),
                    "can_respond": booking.status == "quoted",
                    "price": f"{Decimal(str(price_value or 0)):.2f}",
                }
            )

    return {
        "id": event.pk,
        "title": event.title,
        "event_date": event.event_date.strftime("%Y-%m-%d"),
        "event_date_label": event.event_date.strftime("%A, %B %d, %Y"),
        "event_time": event.event_time.strftime("%H:%M") if event.event_time else "",
        "venue_name": event.venue_name or "Venue not set",
        "venue_address": event.venue_address or "",
        "has_own_venue": bool(event.has_own_venue),
        "notes": event.notes or "",
        "completed_at": event.completed_at,
        "payment_method": event.payment_method or "",
        "payment_method_label": payment_choices.get(
            event.payment_method, "Not selected"
        ),
        "payment_saved_at": (
            event.payment_saved_at.isoformat()
            if event.payment_saved_at
            else ""
        ),
        "created_at": event.created_at.isoformat() if event.created_at else "",
        "total_cost": f"{total_cost:.2f}",
        "service_count": len(service_rows),
        "service_rows": service_rows,
        "service_labels": (
            ", ".join(row["service_name"] for row in service_rows)
            if service_rows
            else "No services booked"
        ),
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
        queryset = (
            event_model.objects.filter(client=request.user)
            .prefetch_related(
                "service_requests__service", "service_requests__vendor"
            )
            .order_by("-event_date", "-created_at")
        )
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
def client_event_detail_view(
    request: HttpRequest, event_id: int
) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    event = get_object_or_404(
        Event.objects.prefetch_related(
            "service_requests__service", "service_requests__vendor"
        ),
        pk=event_id,
        client=request.user,
    )
    selected_event = _serialize_client_event(event)
    
    # Only approved bookings can be paid in checkout; include booking + service IDs.
    rating_services = []
    for booking in event.service_requests.select_related("service").filter(status="approved"):
        service = booking.service
        price_value = booking.quoted_price
        if price_value is None:
            price_value = booking.price_snapshot
        if price_value is None:
            price_value = service.price or 0
        rating_services.append(
            {
                "booking_id": booking.pk,
                "service_id": service.pk,
                "service_name": service.name,
                "service_type": service.get_service_type_display(),
                "price": f"{Decimal(str(price_value)):.2f}",
            }
        )
    modal_target = str(request.GET.get("open", "")).strip().lower()
    detail_url = reverse("events:client_event_detail", kwargs={"event_id": event.pk})
    today = timezone.localdate()
    days_until_event = (event.event_date - today).days
    
    # Logic for completion and deletion
    can_complete_event = today >= event.event_date
    can_delete_event = days_until_event > 2 or days_until_event < -1
    
    # Reason messages for greyed-out buttons
    complete_reason = None
    delete_reason = None
    
    if not can_complete_event:
        complete_reason = f"Available on {event.event_date.strftime('%A, %B %d')}"
    
    if not can_delete_event:
        if days_until_event == -1:
            delete_reason = "Cannot delete events that occurred yesterday"
        elif days_until_event == 0:
            delete_reason = "Cannot delete today's events"
        elif days_until_event == 1:
            delete_reason = "Cannot delete tomorrow's events"
        elif days_until_event == 2:
            delete_reason = "Cannot delete events within 3 days"
        else:
            delete_reason = "Cannot delete past events"
    
    context = client_base_context(request, "my_events")
    context.update(
        {
            "page_name": "Event Details",
            "selected_event": selected_event,
            "event": selected_event,
            "event_form": EventForm(instance=event),
            "back_url": reverse("events:client_my_events"),
            "edit_url": f"{detail_url}?{urlencode({'open': 'edit'})}",
            "complete_url": f"{detail_url}?{urlencode({'open': 'complete'})}",
            "delete_url": reverse("events:client_event_delete", args=[event.pk]),
            "open_edit_modal": modal_target == "edit",
            "open_complete_modal": modal_target == "complete",
            "can_complete_event": can_complete_event,
            "can_delete_event": can_delete_event,
            "complete_reason": complete_reason,
            "delete_reason": delete_reason,
            "update_url": reverse(
                "events:client_event_update", args=[event.pk]
            ),
            "rating_services_json": json.dumps(rating_services),
        }
    )
    return render(request, "users/client/event_detail.html", context)


@login_required(login_url="users:login")
@require_POST
def client_booking_quote_response_view(
    request: HttpRequest, booking_id: int
) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    decision = str(request.POST.get("decision", "")).strip().lower()
    if decision not in {"accept", "reject"}:
        return redirect(
            add_auth_notice(
                reverse("events:client_my_events"),
                AUTH_MESSAGE_KEYS["quote_update_failed"],
            )
        )

    booking = get_object_or_404(
        EventServiceBooking.objects.select_related("event", "service"),
        pk=booking_id,
        event__client=request.user,
        status="quoted",
    )

    if decision == "accept":
        booking.status = "approved"
        booking.price_snapshot = (
            booking.quoted_price
            if booking.quoted_price is not None
            else booking.price_snapshot
        )
        booking.responded_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "price_snapshot",
                "responded_at",
                "updated_at",
            ]
        )
        notify_user(
            booking.service.vendor,
            "Quote accepted",
            f"Your quote for '{booking.service.name}' was accepted.",
            category="approval",
            link_url=reverse("events:vendor_booking_requests"),
        )
        message_key = "quote_accepted"
        system_message = (
            f"System: Client accepted the quote for '{booking.service.name}' on '{booking.event.title}'."
        )
    else:
        booking.status = "rejected"
        booking.responded_at = timezone.now()
        booking.save(update_fields=["status", "responded_at", "updated_at"])
        notify_user(
            booking.service.vendor,
            "Quote rejected",
            f"Your quote for '{booking.service.name}' was rejected.",
            category="request",
            link_url=reverse("events:vendor_booking_requests"),
        )
        message_key = "quote_rejected"
        system_message = (
            f"System: Client rejected the quote for '{booking.service.name}' on '{booking.event.title}'."
        )

    from chat.models import Conversation, Message

    conv, _ = Conversation.objects.get_or_create(
        client=booking.event.client, vendor=booking.service.vendor
    )
    Message.objects.create(
        conversation=conv,
        is_system=True,
        content=system_message,
    )

    return redirect(
        add_auth_notice(
            reverse("events:client_event_detail", kwargs={"event_id": booking.event.pk}),
            AUTH_MESSAGE_KEYS[message_key],
        )
    )


@login_required(login_url="users:login")
@require_POST
def client_event_create_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    form = EventForm(request.POST)
    if not form.is_valid():
        error_messages = [
            f"{field}: {', '.join(errors)}"
            for field, errors in form.errors.items()
        ]
        error_msg = " | ".join(error_messages)
        return redirect(
            add_auth_notice(
                reverse("events:client_my_events"),
                f"Invalid input: {error_msg}",
            )
        )

    event = form.save(commit=False)
    event.client = request.user
    event.save()
    notify_user(
        request.user,
        "Event created",
        f"Your event '{event.title}' was created.",
        category="system",
        link_url=reverse("events:client_my_events"),
    )
    return redirect(
        add_auth_notice(
            reverse("events:client_my_events"),
            AUTH_MESSAGE_KEYS["event_created"],
        )
    )


@login_required(login_url="users:login")
@require_POST
def client_event_update_view(
    request: HttpRequest, event_id: int
) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    event = get_object_or_404(Event, pk=event_id, client=request.user)
    form = EventForm(request.POST, instance=event)
    if form.is_valid():
        form.save()
        notify_user(
            request.user,
            "Event updated",
            f"Your event '{event.title}' was updated.",
            category="system",
            link_url=reverse("events:client_my_events"),
        )
        return redirect(
            add_auth_notice(
                f"{reverse('events:client_my_events')}?event={event.pk}",
                AUTH_MESSAGE_KEYS["event_updated"],
            )
        )

    error_messages = [
        f"{field}: {', '.join(errors)}"
        for field, errors in form.errors.items()
    ]
    error_msg = " | ".join(error_messages)
    return redirect(
        add_auth_notice(
            f"{reverse('events:client_my_events')}?event={event.pk}",
            f"Update failed: {error_msg}",
        )
    )


@login_required(login_url="users:login")
@require_POST
def client_event_payment_view(
    request: HttpRequest, event_id: int
) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    event = get_object_or_404(Event, pk=event_id, client=request.user)
    form = EventPaymentForm(request.POST)
    if form.is_valid():
        event.payment_method = form.cleaned_data["payment_method"]
        event.payment_saved_at = timezone.now()
        event.save(
            update_fields=["payment_method", "payment_saved_at", "updated_at"]
        )
        notify_user(
            request.user,
            "Payment updated",
            f"Your payment method for '{event.title}' was saved.",
            category="system",
            link_url=reverse("events:client_my_events"),
        )
        return redirect(
            add_auth_notice(
                f"{reverse('events:client_my_events')}?event={event.pk}",
                AUTH_MESSAGE_KEYS["payment_updated"],
            )
        )

    return redirect(
        add_auth_notice(
            f"{reverse('events:client_my_events')}?event={event.pk}",
            AUTH_MESSAGE_KEYS["payment_update_failed"],
        )
    )


@login_required(login_url="users:login")
@login_required(login_url="users:login")
@require_POST
def client_event_delete_view(
    request: HttpRequest, event_id: int
) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    event = get_object_or_404(Event, pk=event_id, client=request.user)
    
    # Check if event is within 3 days (cannot delete)
    today = timezone.localdate()
    days_until_event = (event.event_date - today).days
    if days_until_event >= -1 and days_until_event <= 2:  # -1 (today) to 2 (within 3 days)
        return redirect(
            add_auth_notice(
                f"{reverse('events:client_my_events')}?event={event.pk}",
                "event_delete_restricted",
            )
        )
    
    if event.service_requests.exists():
        return redirect(
            add_auth_notice(
                f"{reverse('events:client_my_events')}?event={event.pk}",
                AUTH_MESSAGE_KEYS["event_delete_failed"],
            )
        )

    event.delete()
    return redirect(
        add_auth_notice(
            reverse("events:client_my_events"),
            AUTH_MESSAGE_KEYS["event_deleted"],
        )
    )


@login_required(login_url="users:login")
@require_GET
def vendor_events_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    context = vendor_base_context(request, "events")

    from users.services import _serialize_booking_request

    queryset = (
        EventServiceBooking.objects.select_related(
            "event", "service", "service__vendor"
        )
        .filter(vendor=request.user, status="approved")
        .order_by("-requested_date")
    )
    approved_events = [_serialize_booking_request(item) for item in queryset]

    context.update({"page_name": "Events", "approved_events": approved_events})
    return render(request, "users/vendor/events.html", context)


@login_required(login_url="users:login")
@require_GET
def vendor_event_detail_view(request: HttpRequest, event_id: int) -> HttpResponse:
    """Display event details for vendor - shows the event and their services for it."""
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    # Get the event and verify vendor has a service booking for it
    event = get_object_or_404(
        Event.objects.prefetch_related(
            "service_requests__service", "service_requests__vendor"
        ),
        pk=event_id,
    )
    
    # Get vendor's services for this event
    vendor_bookings = event.service_requests.filter(
        vendor=request.user, status="approved"
    ).select_related("service")
    
    if not vendor_bookings.exists():
        return redirect("events:vendor_events")
    
    # Serialize event details
    event_data = {
        "id": event.pk,
        "title": event.title,
        "event_date": event.event_date.strftime("%Y-%m-%d"),
        "event_date_label": event.event_date.strftime("%A, %B %d, %Y"),
        "event_time": event.event_time.strftime("%H:%M") if event.event_time else "Not specified",
        "venue_name": event.venue_name or "Venue not set",
        "venue_address": event.venue_address or "",
        "notes": event.notes or "",
        "client_name": event.client.get_full_name() or event.client.email,
        "client_phone": event.client.phone or "Not provided",
    }
    
    # Serialize vendor's services for this event
    vendor_services = []
    for booking in vendor_bookings:
        vendor_services.append({
            "service_name": booking.service.name,
            "service_type": booking.service.get_service_type_display(),
            "price": f"{booking.quoted_price or booking.price_snapshot or booking.service.price or 0:.2f}",
            "quote_note": booking.quote_note or "",
        })
    
    context = vendor_base_context(request, "events")
    context.update({
        "page_name": f"{event.title} Details",
        "event": event_data,
        "vendor_services": vendor_services,
        "back_url": reverse("events:vendor_events"),
    })
    return render(request, "users/vendor/event_detail.html", context)


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


def _ensure_service_availability(
    service: Service, days_ahead: int = 90
) -> list[str]:
    today = timezone.localdate()
    dates = []
    for offset in range(days_ahead):
        slot_date = today + timedelta(days=offset)
        ServiceAvailabilitySlot.objects.get_or_create(
            service=service, available_date=slot_date
        )
        dates.append(slot_date.strftime("%Y-%m-%d"))
    return dates


# ── Rating System Endpoints ───────────────────────────────────────────────────

@login_required(login_url="users:login")
@require_POST
def event_complete_view(request: HttpRequest, event_id: int) -> HttpResponse:
    """
    Mark an event as completed. Only the client who owns the event can complete it.
    Returns JSON response.
    """
    from django.http import JsonResponse
    
    event = get_object_or_404(Event, pk=event_id)
    
    # Only the client who owns the event can mark it as complete
    if event.client != request.user:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    # Event can only be completed from the event date onwards
    today = timezone.localdate()
    if today < event.event_date:
        return JsonResponse(
            {"error": "Event cannot be completed before its scheduled date"},
            status=400
        )
    
    # Mark as completed
    event.completed_at = timezone.now()
    event.save()
    
    return JsonResponse({"status": "success", "message": "Event marked as completed"})


def _service_availability_dates(service: Service) -> list[str]:
    slots = list(
        service.availability_slots.filter(is_active=True)
        .order_by("available_date")
        .values_list("available_date", flat=True)
    )
    if not slots:
        slots = [
            timezone.localdate() + timedelta(days=offset)
            for offset in range(90)
        ]
        for slot_date in slots:
            ServiceAvailabilitySlot.objects.get_or_create(
                service=service, available_date=slot_date
            )
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
