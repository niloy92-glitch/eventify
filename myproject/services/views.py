from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, IntegerField, Q, Value, When
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


SERVICE_PAGE_SIZE = 8
SERVICE_SORT_CHOICES = [
    ("newest", "Newest"),
    ("price_low", "Price: Low to high"),
    ("price_high", "Price: High to low"),
    ("rating_high", "Top rated"),
]
SERVICE_MIN_RATING_CHOICES = [
    ("", "Any rating"),
    ("4.5", "4.5+ stars"),
    ("4", "4+ stars"),
    ("3", "3+ stars"),
    ("2", "2+ stars"),
]


def _parse_decimal_filter(raw_value: str) -> Decimal | None:
    raw_value = str(raw_value).strip()
    if not raw_value:
        return None
    try:
        return Decimal(raw_value)
    except (InvalidOperation, TypeError):
        return None


def _get_service_filter_state(request: HttpRequest) -> dict:
    valid_categories = {choice[0] for choice in Service.SERVICE_TYPES}
    valid_sort_values = {choice[0] for choice in SERVICE_SORT_CHOICES}

    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    min_price_raw = request.GET.get("min_price", "").strip()
    max_price_raw = request.GET.get("max_price", "").strip()
    min_rating_raw = request.GET.get("min_rating", "").strip()
    sort = request.GET.get("sort", "newest").strip() or "newest"

    filters = {
        "search": search,
        "category": category if category in valid_categories else "",
        "min_price": _parse_decimal_filter(min_price_raw),
        "max_price": _parse_decimal_filter(max_price_raw),
        "min_rating": _parse_decimal_filter(min_rating_raw),
        "sort": sort if sort in valid_sort_values else "newest",
    }
    display_values = {
        "q": filters["search"],
        "category": filters["category"],
        "min_price": str(filters["min_price"]) if filters["min_price"] is not None else "",
        "max_price": str(filters["max_price"]) if filters["max_price"] is not None else "",
        "min_rating": str(filters["min_rating"]) if filters["min_rating"] is not None else "",
        "sort": filters["sort"],
    }
    filters_active = any(
        [
            bool(filters["search"]),
            bool(filters["category"]),
            filters["min_price"] is not None,
            filters["max_price"] is not None,
            filters["min_rating"] is not None,
            filters["sort"] != "newest",
        ]
    )
    return {
        "filters": filters,
        "display_values": display_values,
        "filters_active": filters_active,
    }


def _apply_service_filters(queryset, filters: dict):
    queryset = queryset.select_related("vendor").annotate(
        avg_rating=Avg("ratings__stars", filter=Q(ratings__status="approved")),
        rating_count=Count("ratings", filter=Q(ratings__status="approved")),
        has_price=Case(
            When(price__isnull=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    )

    search = filters["search"]
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(vendor__company_name__icontains=search)
            | Q(vendor__first_name__icontains=search)
            | Q(vendor__last_name__icontains=search)
            | Q(vendor__email__icontains=search)
        )

    if filters["category"]:
        queryset = queryset.filter(service_type=filters["category"])

    if filters["min_price"] is not None:
        queryset = queryset.filter(price__gte=filters["min_price"])

    if filters["max_price"] is not None:
        queryset = queryset.filter(price__lte=filters["max_price"])

    if filters["min_rating"] is not None:
        queryset = queryset.filter(avg_rating__gte=filters["min_rating"])

    sort = filters["sort"]
    if sort == "price_low":
        queryset = queryset.order_by("has_price", "price", "-created_at")
    elif sort == "price_high":
        queryset = queryset.order_by("has_price", "-price", "-created_at")
    elif sort == "rating_high":
        queryset = queryset.order_by("-avg_rating", "-created_at")
    else:
        queryset = queryset.order_by("-created_at")

    return queryset


def _service_listing_page(request: HttpRequest, queryset, page_size: int = SERVICE_PAGE_SIZE):
    service_filter_state = _get_service_filter_state(request)
    filtered_queryset = _apply_service_filters(queryset, service_filter_state["filters"])
    paginator = Paginator(filtered_queryset, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return {
        "filters": service_filter_state["filters"],
        "display_values": service_filter_state["display_values"],
        "filters_active": service_filter_state["filters_active"],
        "paginator": paginator,
        "page_obj": page_obj,
        "query_string": query_params.urlencode(),
        "service_types": Service.SERVICE_TYPES,
        "sort_choices": SERVICE_SORT_CHOICES,
        "rating_choices": SERVICE_MIN_RATING_CHOICES,
    }


@login_required(login_url="users:login")
@require_GET
def vendor_service_list(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")

    context = vendor_base_context(request, "services")
    queryset = Service.objects.filter(vendor=request.user).prefetch_related(
        "approval_requests"
    )
    listing_page = _service_listing_page(request, queryset)
    services_with_status = []
    for service in listing_page["page_obj"].object_list:
        approval_request = service.approval_requests.first()
        services_with_status.append(
            {
                "service": service,
                "approval_status": approval_request.status if approval_request else None,
                "avg_rating": service.avg_rating,
                "rating_count": service.rating_count,
            }
        )

    context.update(
        {
            "services": services_with_status,
            "page_obj": listing_page["page_obj"],
            "paginator": listing_page["paginator"],
            "query_string": listing_page["query_string"],
            "service_types": listing_page["service_types"],
            "sort_choices": listing_page["sort_choices"],
            "rating_choices": listing_page["rating_choices"],
            "service_filters": listing_page["display_values"],
            "service_filters_active": listing_page["filters_active"],
            "page_name": "Services",
        }
    )
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
def vendor_service_profile(request: HttpRequest, pk: int) -> HttpResponse:
    """Display service profile/details page for vendor."""
    service = get_object_or_404(Service, pk=pk, vendor=request.user)
    
    # Get all events that have booked this service (approved bookings)
    booked_events = EventServiceBooking.objects.filter(
        service=service,
        status="approved"
    ).select_related("event").values(
        "event_id", "event__title", "event__event_date"
    ).order_by("-event__event_date")

    from services.rating_utils import (
        get_service_avg_rating,
        get_service_rating_count,
        get_vendor_avg_rating,
    )

    service_avg_rating = get_service_avg_rating(service.pk)
    service_rating_count = get_service_rating_count(service.pk)
    vendor_avg_rating = get_vendor_avg_rating(request.user.pk)
    
    context = vendor_base_context(request, "services")
    context.update({
        "service": service,
        "booked_events": booked_events,
        "service_avg_rating": service_avg_rating,
        "service_rating_count": service_rating_count,
        "vendor_avg_rating": vendor_avg_rating,
        "page_name": service.name,
    })
    return render(request, "services/vendor/profile.html", context)


@login_required(login_url="users:login")
@require_GET
def services_home(request: HttpRequest) -> HttpResponse:
    # show all approved services to clients
    context = client_base_context(request, "home")
    queryset = Service.objects.filter(is_approved=True).prefetch_related(
        "availability_slots"
    )
    listing_page = _service_listing_page(request, queryset)
    services = list(listing_page["page_obj"].object_list)
    services_payload = []

    booked_event_map = {}
    booked_event_rows = EventServiceBooking.objects.filter(
        service__in=services,
        event__client=request.user,
        status__in=["quoted", "approved"],
    ).values_list("service_id", "event_id")
    for service_id, event_id in booked_event_rows:
        booked_event_map.setdefault(service_id, []).append(event_id)

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
                "price": str(service.price) if service.price is not None else "",
                "availability_dates": availability_dates,
                "booked_event_ids": booked_event_map.get(service.pk, []),
                "avg_rating": float(service.avg_rating)
                if getattr(service, "avg_rating", None) is not None
                else None,
                "rating_count": int(service.rating_count or 0),
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
            "page_obj": listing_page["page_obj"],
            "paginator": listing_page["paginator"],
            "query_string": listing_page["query_string"],
            "service_types": listing_page["service_types"],
            "sort_choices": listing_page["sort_choices"],
            "rating_choices": listing_page["rating_choices"],
            "service_filters": listing_page["display_values"],
            "service_filters_active": listing_page["filters_active"],
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

    elif decision == "approve":
        # Vendor directly approves the booking request (without quoting)
        booking.status = "approved"
        booking.responded_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "responded_at",
                "updated_at",
            ]
        )
        notify_user(
            booking.event.client,
            "Booking approved",
            f"Your request for '{booking.service.name}' was approved.",
            category="approval",
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
            content=f"System: Vendor approved the booking request for '{booking.service.name}'.",
        )

        return redirect(
            add_auth_notice(
                reverse("users:vendor_dashboard"),
                AUTH_MESSAGE_KEYS["booking_updated"],
            )
        )

    elif decision == "reject":
        # Vendor rejects the booking request
        booking.status = "rejected"
        booking.responded_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "responded_at",
                "updated_at",
            ]
        )
        notify_user(
            booking.event.client,
            "Booking rejected",
            f"Your request for '{booking.service.name}' was rejected.",
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
            content=f"System: Vendor rejected the booking request for '{booking.service.name}'.",
        )

        return redirect(
            add_auth_notice(
                reverse("users:vendor_dashboard"),
                AUTH_MESSAGE_KEYS["booking_updated"],
            )
        )


# ── Rating System Endpoints ───────────────────────────────────────────────────

@login_required(login_url="users:login")
@require_POST
def service_rate_view(request: HttpRequest, service_id: int) -> HttpResponse:
    """
    Submit a rating for a service for a specific event.
    Only the client who attended the event can rate.
    Returns JSON response.
    """
    from django.http import JsonResponse
    import json
    from services.models import ServiceRating
    from services.rating_utils import create_service_rating
    
    service = get_object_or_404(Service, pk=service_id)
    
    try:
        data = json.loads(request.body)
        event_id = data.get("event_id")
        stars = data.get("stars")
        
        if not event_id or stars is None:
            return JsonResponse(
                {"error": "Missing event_id or stars"},
                status=400
            )
        
        event = get_object_or_404(Event, pk=event_id)
        
        # Verify the client attended this event
        if event.client != request.user:
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        # Verify the service was booked for this event
        booking = EventServiceBooking.objects.filter(
            event=event,
            service=service,
            status="approved"
        ).first()
        
        if not booking:
            return JsonResponse(
                {"error": "Service was not booked for this event"},
                status=400
            )
        
        # Create the rating
        try:
            rating = create_service_rating(
                client=request.user,
                service=service,
                event=event,
                stars=int(stars)
            )
            return JsonResponse({
                "status": "success",
                "message": "Rating submitted for admin approval",
                "rating_id": rating.id
            })
        except ValueError as e:
            return JsonResponse(
                {"error": str(e)},
                status=400
            )
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400
        )


@login_required(login_url="users:login")
@require_GET
def service_rating_view(request: HttpRequest, service_id: int) -> HttpResponse:
    """
    Get the average rating for a service (public endpoint).
    Returns JSON response with avg_rating, count, and vendor_avg.
    """
    from django.http import JsonResponse
    from services.rating_utils import (
        get_service_avg_rating,
        get_service_rating_count,
        get_vendor_avg_rating,
    )
    
    service = get_object_or_404(Service, pk=service_id)
    
    avg_rating = get_service_avg_rating(service_id)
    count = get_service_rating_count(service_id)
    vendor_avg = get_vendor_avg_rating(service.vendor_id)
    
    return JsonResponse({
        "service_id": service_id,
        "avg_rating": float(avg_rating) if avg_rating else None,
        "rating_count": count,
        "vendor_avg_rating": float(vendor_avg) if vendor_avg else None,
    })

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
