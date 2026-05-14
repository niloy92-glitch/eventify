from __future__ import annotations

from datetime import date, datetime, timedelta

from django.db.models import Avg
from django.utils import timezone

from services.models import Service, ServiceRating
from events.models import Event, EventServiceBooking


def _completion_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return timezone.localtime(value).date()
    if isinstance(value, date):
        return value
    return None


def is_rating_window_open(completed_at, today: date | None = None) -> bool:
    completed_date = _completion_date(completed_at)
    if completed_date is None:
        return False
    current_day = today or timezone.localdate()
    return completed_date <= current_day <= completed_date + timedelta(days=7)


def can_client_rate_service(client, service: Service, event: Event, today: date | None = None) -> bool:
    if event.client_id != getattr(client, "pk", None):
        return False
    if event.completed_at is None or not is_rating_window_open(event.completed_at, today=today):
        return False
    return EventServiceBooking.objects.filter(
        event=event,
        service=service,
        status="approved",
    ).exists()


def create_service_rating(*, client, service: Service, event: Event, stars: int) -> ServiceRating:
    try:
        star_value = int(stars)
    except (TypeError, ValueError) as exc:
        raise ValueError("Stars must be an integer between 1 and 5.") from exc

    if star_value < 1 or star_value > 5:
        raise ValueError("Stars must be between 1 and 5.")

    if not can_client_rate_service(client, service, event):
        raise ValueError("Rating window is closed or the booking is not eligible.")

    if ServiceRating.objects.filter(service=service, client=client, event=event).exists():
        raise ValueError("You have already rated this service for this event.")

    return ServiceRating.objects.create(
        service=service,
        client=client,
        event=event,
        stars=star_value,
        status="pending",
    )


def get_service_avg_rating(service_id: int):
    return (
        ServiceRating.objects.filter(service_id=service_id, status="approved")
        .aggregate(avg=Avg("stars"))["avg"]
    )


def get_service_rating_count(service_id: int) -> int:
    return ServiceRating.objects.filter(service_id=service_id, status="approved").count()


def get_vendor_avg_rating(vendor_id: int):
    return (
        ServiceRating.objects.filter(service__vendor_id=vendor_id, status="approved")
        .aggregate(avg=Avg("stars"))["avg"]
    )