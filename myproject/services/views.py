from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .models import ApprovalRequest, Service, ServiceAvailabilitySlot
from events.models import Event
from .forms import ServiceForm
from users.services import AUTH_MESSAGE_KEYS, add_auth_notice, client_base_context, vendor_base_context


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
        "event_date_label": event.event_date.strftime("%A, %B %d, %Y"),
        "venue_name": event.venue_name or "Venue not set",
        "has_own_venue": bool(event.has_own_venue),
    }


def _booking_status_badge(status: str) -> str:
    if status == "approved":
        return "confirmed"
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
            ApprovalRequest.objects.create(request_type="service", service=service, vendor=request.user)
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
    context.update({"form": form, "service": service, "page_name": "Edit Service"})
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
    services = list(Service.objects.select_related("vendor").prefetch_related("availability_slots").filter(is_approved=True))
    services_payload = []
    for service in services:
        availability_dates = _service_availability_dates(service)
        service.availability_dates_json = availability_dates
        services_payload.append(
            {
                "id": service.pk,
                "name": service.name,
                "description": service.description,
                "company_name": service.vendor.company_name or service.vendor.get_full_name(),
                "service_type": service.service_type,
                "is_approved": service.is_approved,
                "price": str(service.price) if service.price is not None else "",
                "availability_dates": availability_dates,
            }
        )

    upcoming_events = []
    try:
        event_queryset = Event.objects.filter(client=request.user, event_date__gte=timezone.localdate()).order_by("event_date", "created_at")
        upcoming_events = [_serialize_upcoming_event(event) for event in event_queryset]
    except Exception:
        upcoming_events = []

    context.update({"services": services, "services_payload": services_payload, "page_name": "Home", "client_upcoming_events_payload": upcoming_events})
    return render(request, "services/client/home.html", context)


