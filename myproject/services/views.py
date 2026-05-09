from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import (
    require_http_methods,
    require_GET,
    require_POST,
)
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model

from services.models import ApprovalRequest, Service, ServiceAvailabilitySlot
from events.models import Event, EventServiceBooking
from services.forms import ServiceForm
from users.services import (
    AUTH_MESSAGE_KEYS,
    add_auth_notice,
    client_base_context,
    notify_user,
    vendor_base_context,
)


User = get_user_model()


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
        "event_date_label": event.event_date.strftime("%A, %B %d, %Y"),
        "venue_name": event.venue_name or "Venue not set",
        "has_own_venue": bool(event.has_own_venue),
    }


def _booking_status_badge(status: str) -> str:
    if status == "approved":
        return "confirmed"
    if status == "quoted":
        return "info-tag"
    if status == "rejected":
        return "rejected"
    return "pending"


@login_required(login_url="users:login")
@require_GET
def vendor_service_list(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")

    context = vendor_base_context(request, "services")
    services = Service.objects.filter(vendor=request.user)
    context.update({"services": services, "page_name": "Services"})
    return render(request, "services/vendor/list.html", context)


@login_required(login_url="users:login")
@require_http_methods(["GET", "POST"])
def vendor_service_create(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")

    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.vendor = request.user
            service.is_approved = False
            service.save()
            _ensure_service_availability(service)
            # create an approval request for admin
            ApprovalRequest.objects.create(
                request_type="service", service=service, vendor=request.user
            )
            for admin_user in User.objects.filter(
                role="admin", is_active=True
            ):
                notify_user(
                    admin_user,
                    "New service request",
                    f"{request.user.get_full_name()} submitted '{service.name}' for approval.",
                    category="request",
                    link_url=reverse("users:admin_approvals"),
                )
            notify_user(
                request.user,
                "Service submitted",
                f"Your service '{service.name}' is waiting for approval.",
                category="request",
                link_url=reverse("services:vendor_services"),
            )
            return redirect(reverse("services:vendor_services"))
    else:
        form = ServiceForm()

    context = vendor_base_context(request, "services")
    context.update({"form": form, "page_name": "Create Service"})
    return render(request, "services/vendor/form.html", context)


@login_required(login_url="users:login")
@require_http_methods(["GET", "POST"])
def vendor_service_edit(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service, pk=pk, vendor=request.user)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect(reverse("services:vendor_services"))
    else:
        form = ServiceForm(instance=service)

    context = vendor_base_context(request, "services")
    context.update(
        {"form": form, "service": service, "page_name": "Edit Service"}
    )
    return render(request, "services/vendor/form.html", context)


@login_required(login_url="users:login")
@require_POST
def vendor_service_delete(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service, pk=pk, vendor=request.user)
    service.delete()
    return redirect(reverse("services:vendor_services"))


@login_required(login_url="users:login")
@require_GET
def services_home(request: HttpRequest) -> HttpResponse:
    # show all approved services to clients
    context = client_base_context(request, "home")
    services = list(
        Service.objects.select_related("vendor")
        .prefetch_related("availability_slots")
        .filter(is_approved=True)
    )
    services_payload = []
    for service in services:
        availability_dates = _service_availability_dates(service)
        service.availability_dates_json = availability_dates
        services_payload.append(
            {
                "id": service.pk,
                "name": service.name,
                "description": service.description,
                "company_name": service.vendor.company_name
                or service.vendor.get_full_name(),
                "service_type": service.service_type,
                "is_approved": service.is_approved,
                "price": (
                    str(service.price) if service.price is not None else ""
                ),
                "availability_dates": availability_dates,
            }
        )

    upcoming_events = []
    try:
        event_queryset = Event.objects.filter(
            client=request.user, event_date__gte=timezone.localdate()
        ).order_by("event_date", "created_at")
        upcoming_events = [
            _serialize_upcoming_event(event) for event in event_queryset
        ]
    except Exception:
        upcoming_events = []

    context.update(
        {
            "services": services,
            "services_payload": services_payload,
            "page_name": "Home",
            "client_upcoming_events_payload": upcoming_events,
        }
    )
    return render(request, "services/client/home.html", context)


@login_required(login_url="users:login")
@require_POST
def book_service_request(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "client":
        return redirect("users:login")

    service_id = str(request.POST.get("service_id", "")).strip()
    event_id = str(request.POST.get("event_id", "")).strip()

    if not service_id.isdigit() or not event_id.isdigit():
        return redirect(
            add_auth_notice(
                reverse("services:services_home"),
                "Invalid service or event ID.",
            )
        )

    service = get_object_or_404(
        Service.objects.select_related("vendor"),
        pk=int(service_id),
        is_approved=True,
    )
    event = get_object_or_404(Event, pk=int(event_id), client=request.user)

    if service.service_type == "venue" and event.has_own_venue:
        return redirect(
            add_auth_notice(
                reverse("services:services_home"),
                "This event already has its own venue, so venue services are blocked.",
            )
        )

    if event.event_date < timezone.localdate():
        return redirect(
            add_auth_notice(
                reverse("services:services_home"),
                "Cannot book a service for a past event.",
            )
        )

    if not ServiceAvailabilitySlot.objects.filter(
        service=service, available_date=event.event_date, is_active=True
    ).exists():
        return redirect(
            add_auth_notice(
                reverse("services:services_home"),
                "This event date does not match an available slot on the calendar.",
            )
        )

    booking, created = EventServiceBooking.objects.get_or_create(
        event=event,
        service=service,
        defaults={
            "vendor": service.vendor,
            "requested_date": event.event_date,
            "price_snapshot": service.price,
            "quoted_price": None,
            "quote_note": "",
            "quoted_at": None,
            "status": "pending",
        },
    )
    if not created and booking.status != "approved":
        booking.vendor = service.vendor
        booking.requested_date = event.event_date
        booking.price_snapshot = service.price
        booking.quoted_price = None
        booking.quote_note = ""
        booking.quoted_at = None
        booking.status = "pending"
        booking.save(
            update_fields=[
                "vendor",
                "requested_date",
                "price_snapshot",
                "quoted_price",
                "quote_note",
                "quoted_at",
                "status",
                "updated_at",
            ]
        )

    notify_user(
        service.vendor,
        "New booking request",
        f"{request.user.get_full_name()} requested '{service.name}' for '{event.title}'.",
        category="request",
        link_url=reverse("events:vendor_booking_requests"),
    )
    notify_user(
        request.user,
        "Booking requested",
        f"Your booking request for '{service.name}' was sent.",
        category="request",
        link_url=reverse("events:client_my_events"),
    )

    from chat.models import Conversation, Message

    conv, _ = Conversation.objects.get_or_create(
        client=event.client, vendor=service.vendor
    )
    Message.objects.create(
        conversation=conv,
        is_system=True,
        content=f"System: Client requested to book '{service.name}' for '{event.title}' on {event.event_date.strftime('%B %d, %Y')}.",
    )

    msg = AUTH_MESSAGE_KEYS["booking_requested"]
    return redirect(add_auth_notice(reverse("services:services_home"), msg))


@login_required(login_url="users:login")
@require_POST
def vendor_booking_request_update(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")

    request_id = str(request.POST.get("request_id", "")).strip()
    decision = str(request.POST.get("decision", "")).strip().lower()
    quote_price_value = str(request.POST.get("quote_price", "")).strip()
    quote_note = str(request.POST.get("quote_note", "")).strip()
    if not request_id.isdigit() or decision not in {"approve", "reject", "quote"}:
        return redirect(
            add_auth_notice(
                reverse("users:vendor_dashboard"),
                AUTH_MESSAGE_KEYS["booking_update_failed"],
            )
        )

    booking = get_object_or_404(
        EventServiceBooking.objects.select_related("service", "event"),
        pk=int(request_id),
        service__vendor=request.user,
    )

    if decision == "quote":
        try:
            quoted_price = Decimal(quote_price_value)
        except (InvalidOperation, TypeError):
            quoted_price = None
        if quoted_price is None or quoted_price <= 0:
            return redirect(
                add_auth_notice(
                    reverse("users:vendor_dashboard"),
                    AUTH_MESSAGE_KEYS["quote_update_failed"],
                )
            )

        booking.status = "quoted"
        booking.quoted_price = quoted_price
        booking.quote_note = quote_note[:1000]
        booking.quoted_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "quoted_price",
                "quote_note",
                "quoted_at",
                "updated_at",
            ]
        )
        notify_user(
            booking.event.client,
            "Quote received",
            f"{request.user.get_full_name()} sent a quote of BDT {quoted_price:.2f} for '{booking.service.name}'.",
            category="request",
            link_url=reverse(
                "events:client_event_detail",
                kwargs={"event_id": booking.event.pk},
            ),
        )

        from chat.models import Conversation, Message

        conv, _ = Conversation.objects.get_or_create(
            client=booking.event.client, vendor=booking.service.vendor
        )
        Message.objects.create(
            conversation=conv,
            is_system=True,
            content=f"System: Vendor sent a quote of BDT {quoted_price:.2f} for '{booking.service.name}' on '{booking.event.title}'.",
        )

        return redirect(
            add_auth_notice(
                reverse("users:vendor_dashboard"),
                AUTH_MESSAGE_KEYS["quote_sent"],
            )
        )

    booking.status = "approved" if decision == "approve" else "rejected"
    booking.responded_at = timezone.now()
    booking.save(update_fields=["status", "responded_at", "updated_at"])
    notify_user(
        booking.event.client,
        f"Booking {booking.status}",
        f"Your request for '{booking.service.name}' was {booking.status}.",
        category="approval",
        link_url=reverse("events:client_my_events"),
    )

    from chat.models import Conversation, Message

    conv, _ = Conversation.objects.get_or_create(
        client=booking.event.client, vendor=booking.service.vendor
    )
    status_text = "approved" if decision == "approve" else "rejected"
    Message.objects.create(
        conversation=conv,
        is_system=True,
        content=f"System: Vendor has {status_text} the booking request for '{booking.service.name}'.",
    )

    return redirect(
        add_auth_notice(
            reverse("users:vendor_dashboard"),
            AUTH_MESSAGE_KEYS["booking_updated"],
        )
    )
