from collections import defaultdict
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from uuid import uuid4
import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from events.models import Event, EventServiceBooking
from users.services import (
    AUTH_DEFAULT_ROLE,
    DJANGO_ADMIN_URL,
    add_auth_notice,
    admin_base_context,
    client_base_context,
    is_django_admin_user,
    login_redirect_url,
    normalize_role,
    vendor_base_context,
)
from .forms import VendorPaymentMethodForm
from .models import PaymentMethod, Payout, Transaction, TransactionServiceItem


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


def _admin_access_redirect(request: HttpRequest):
    if is_django_admin_user(request.user):
        return redirect(DJANGO_ADMIN_URL)
    if normalize_role(getattr(request.user, "role", AUTH_DEFAULT_ROLE)) != "admin":
        return redirect(login_redirect_url(getattr(request.user, "role", AUTH_DEFAULT_ROLE)))
    return None


def _booking_total(booking: EventServiceBooking) -> Decimal:
    value = booking.quoted_price
    if value is None:
        value = booking.price_snapshot
    if value is None:
        value = getattr(booking.service, "price", None)
    return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))


def _paid_amount_for_bookings(booking_ids: list[int]) -> dict[int, Decimal]:
    totals = (
        TransactionServiceItem.objects.filter(
            booking_id__in=booking_ids,
            transaction__status="success",
        )
        .values("booking_id")
        .annotate(total_paid=Sum("paid_amount"))
    )
    result: dict[int, Decimal] = {}
    for row in totals:
        result[row["booking_id"]] = Decimal(str(row["total_paid"] or "0.00")).quantize(Decimal("0.01"))
    return result


def _split_proportional(total_amount: Decimal, weights: dict[int, Decimal]) -> dict[int, Decimal]:
    if total_amount <= Decimal("0.00"):
        return {key: Decimal("0.00") for key in weights}

    weight_sum = sum(weights.values())
    if weight_sum <= Decimal("0.00"):
        return {key: Decimal("0.00") for key in weights}

    entries = []
    assigned = Decimal("0.00")
    for key, weight in weights.items():
        ratio_amount = (total_amount * weight / weight_sum)
        floored = ratio_amount.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        remainder = ratio_amount - floored
        assigned += floored
        entries.append([key, floored, remainder])

    cents_left = int(((total_amount - assigned) * 100).to_integral_value())
    entries.sort(key=lambda item: item[2], reverse=True)
    for index in range(cents_left):
        entries[index % len(entries)][1] += Decimal("0.01")

    return {key: amount.quantize(Decimal("0.01")) for key, amount, _ in entries}


@login_required(login_url="users:login")
@require_GET
def client_transactions_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    rows = []
    queryset = Transaction.objects.filter(client=request.user).select_related("event")
    for tx in queryset:
        rows.append(
            {
                "tx_ref": tx.tx_ref,
                "event_title": tx.event.title,
                "amount": f"{tx.amount:.2f}",
                "status_label": tx.get_status_display(),
                "created_at": timezone.localtime(tx.created_at).strftime("%d %b %Y, %I:%M %p"),
            }
        )

    context = client_base_context(request, "transactions")
    context.update({"transactions": rows})
    return render(request, "payment/client_transactions.html", context)


@login_required(login_url="users:login")
def vendor_transactions_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _vendor_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    method = PaymentMethod.objects.filter(vendor=request.user).first()
    if request.method == "POST":
        form = VendorPaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            item = form.save(commit=False)
            item.vendor = request.user
            item.save()
            return redirect(
                add_auth_notice(
                    reverse("payment:vendor_transactions"),
                    "vendor_payment_info_saved",
                )
            )
    else:
        form = VendorPaymentMethodForm(instance=method)

    payout_total = (
        Payout.objects.filter(vendor=request.user).aggregate(total=Sum("gross_amount"))["total"]
        or Decimal("0.00")
    )

    rows = []
    queryset = (
        TransactionServiceItem.objects.filter(vendor=request.user, transaction__status="success")
        .select_related("transaction", "service", "booking__event")
        .order_by("-transaction__created_at")
    )
    for item in queryset:
        rows.append(
            {
                "tx_ref": item.transaction.tx_ref,
                "event_title": item.booking.event.title,
                "service_name": item.service.name,
                "paid_amount": f"{item.paid_amount:.2f}",
                "created_at": timezone.localtime(item.transaction.created_at).strftime("%d %b %Y, %I:%M %p"),
            }
        )

    context = vendor_base_context(request, "transactions")
    context.update(
        {
            "rows": rows,
            "balance": f"{Decimal(str(payout_total)):.2f}",
            "payment_form": form,
        }
    )
    return render(request, "payment/vendor_transactions.html", context)


@login_required(login_url="users:login")
@require_GET
def admin_transactions_view(request: HttpRequest) -> HttpResponse:
    redirect_response = _admin_access_redirect(request)
    if redirect_response is not None:
        return redirect_response

    rows = []
    queryset = Transaction.objects.select_related("event", "client")
    for tx in queryset:
        rows.append(
            {
                "tx_ref": tx.tx_ref,
                "event_title": tx.event.title,
                "client_name": tx.client.get_full_name() or tx.client.email,
                "amount": f"{tx.amount:.2f}",
                "status_label": tx.get_status_display(),
                "created_at": timezone.localtime(tx.created_at).strftime("%d %b %Y, %I:%M %p"),
            }
        )

    context = admin_base_context(request, "transactions")
    context.update({"rows": rows})
    return render(request, "payment/admin_transactions.html", context)


@login_required(login_url="users:login")
@require_POST
def client_event_checkout_view(request: HttpRequest, event_id: int) -> JsonResponse:
    redirect_response = _client_access_redirect(request)
    if redirect_response is not None:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    event = get_object_or_404(Event, pk=event_id, client=request.user)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON body."}, status=400)

    amount_raw = str(payload.get("amount", "")).strip()
    selected_ids = payload.get("selected_booking_ids") or []
    ratings = payload.get("ratings") or {}

    try:
        amount = Decimal(amount_raw).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid amount."}, status=400)

    if amount <= Decimal("0.00"):
        return JsonResponse({"ok": False, "error": "Amount must be greater than 0."}, status=400)

    approved_bookings = list(
        event.service_requests.select_related("service", "vendor").filter(status="approved")
    )
    if not approved_bookings:
        return JsonResponse({"ok": False, "error": "No approved services available for payment."}, status=400)

    all_booking_ids = {booking.pk for booking in approved_bookings}
    normalized_selected_ids = []
    for raw_id in selected_ids:
        try:
            bid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if bid in all_booking_ids:
            normalized_selected_ids.append(bid)

    if not normalized_selected_ids:
        return JsonResponse({"ok": False, "error": "Select at least one service to pay."}, status=400)

    paid_map = _paid_amount_for_bookings(list(all_booking_ids))
    booking_by_id = {booking.pk: booking for booking in approved_bookings}

    outstanding_by_booking = {}
    for booking in approved_bookings:
        total_cost = _booking_total(booking)
        paid = paid_map.get(booking.pk, Decimal("0.00"))
        due = total_cost - paid
        if due < Decimal("0.00"):
            due = Decimal("0.00")
        outstanding_by_booking[booking.pk] = due.quantize(Decimal("0.01"))

    selected_due = sum(outstanding_by_booking.get(bid, Decimal("0.00")) for bid in normalized_selected_ids)
    selected_due = selected_due.quantize(Decimal("0.01"))
    if selected_due <= Decimal("0.00"):
        return JsonResponse({"ok": False, "error": "Selected services have no remaining due."}, status=400)

    if amount > selected_due:
        return JsonResponse(
            {
                "ok": False,
                "error": f"Amount exceeds selected due (BDT {selected_due:.2f}).",
            },
            status=400,
        )

    # Simulation requirement: fail payment when any vendor in this event has missing payment info.
    vendor_ids = sorted({booking.vendor_id for booking in approved_bookings})
    ready_vendor_ids = set(
        PaymentMethod.objects.filter(vendor_id__in=vendor_ids, is_active=True)
        .exclude(account_number="")
        .values_list("vendor_id", flat=True)
    )
    missing_vendor_rows = []
    for booking in approved_bookings:
        if booking.vendor_id not in ready_vendor_ids:
            missing_vendor_rows.append(
                {
                    "vendor": booking.vendor.company_name or booking.vendor.get_full_name() or booking.vendor.email,
                    "service": booking.service.name,
                }
            )

    if missing_vendor_rows:
        tx = Transaction.objects.create(
            tx_ref=f"TXN-{uuid4().hex[:12].upper()}",
            event=event,
            client=request.user,
            amount=amount,
            currency="BDT",
            status="failed",
            failure_reason="Vendor payout info missing",
        )
        return JsonResponse(
            {
                "ok": False,
                "workflow": "failed",
                "transaction_ref": tx.tx_ref,
                "error": "Payment failed because one or more vendors did not add payout info.",
                "missing_vendors": missing_vendor_rows,
            },
            status=400,
        )

    weights = {bid: outstanding_by_booking[bid] for bid in normalized_selected_ids}
    allocation = _split_proportional(amount, weights)

    with transaction.atomic():
        tx = Transaction.objects.create(
            tx_ref=f"TXN-{uuid4().hex[:12].upper()}",
            event=event,
            client=request.user,
            amount=amount,
            currency="BDT",
            status="success",
        )

        payout_totals = defaultdict(lambda: Decimal("0.00"))
        for booking_id, paid_amount in allocation.items():
            if paid_amount <= Decimal("0.00"):
                continue
            booking = booking_by_id[booking_id]
            TransactionServiceItem.objects.create(
                transaction=tx,
                booking=booking,
                service=booking.service,
                vendor=booking.vendor,
                service_total=_booking_total(booking),
                paid_amount=paid_amount,
            )
            payout_totals[booking.vendor_id] += paid_amount

        for vendor_id, gross_amount in payout_totals.items():
            Payout.objects.create(
                transaction=tx,
                vendor_id=vendor_id,
                gross_amount=gross_amount.quantize(Decimal("0.01")),
                currency="BDT",
                status="released",
            )

        if event.completed_at is None:
            event.completed_at = timezone.now()
            event.save(update_fields=["completed_at", "updated_at"])

        # Reuse existing rating system when ratings are provided.
        if ratings:
            from services.rating_utils import create_service_rating

            service_map = {booking.service_id: booking for booking in approved_bookings}
            for raw_service_id, raw_stars in ratings.items():
                try:
                    service_id = int(raw_service_id)
                    stars = int(raw_stars)
                except (TypeError, ValueError):
                    continue
                booking = service_map.get(service_id)
                if not booking:
                    continue
                try:
                    create_service_rating(
                        client=request.user,
                        service=booking.service,
                        event=event,
                        stars=stars,
                    )
                except Exception:
                    # Ignore duplicate/invalid rating errors in checkout flow.
                    continue

    event_total = sum(_booking_total(booking) for booking in approved_bookings)
    event_paid_after = (
        TransactionServiceItem.objects.filter(
            booking__event=event,
            transaction__status="success",
        ).aggregate(total=Sum("paid_amount"))["total"]
        or Decimal("0.00")
    )
    due_after = (Decimal(str(event_total)) - Decimal(str(event_paid_after))).quantize(Decimal("0.01"))
    if due_after < Decimal("0.00"):
        due_after = Decimal("0.00")

    return JsonResponse(
        {
            "ok": True,
            "workflow": "success",
            "transaction_ref": tx.tx_ref,
            "paid_amount": f"{amount:.2f}",
            "due_after": f"{due_after:.2f}",
            "message": "Payment completed and event marked as completed.",
        }
    )
