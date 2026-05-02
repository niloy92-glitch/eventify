from django.db import models
from django.conf import settings


class Event(models.Model):
    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("mobile_banking", "Mobile Banking"),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=150)
    event_date = models.DateField()
    venue_name = models.CharField(max_length=150, blank=True)
    venue_address = models.TextField(blank=True)
    has_own_venue = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, blank=True, default="")
    payment_saved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.event_date})"


class EventServiceBooking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="service_requests")
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE, related_name="event_service_requests")
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="booking_requests")
    requested_date = models.DateField()
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "service"], name="unique_event_service_booking"),
        ]

    def __str__(self) -> str:
        return f"{self.event} -> {self.service} ({self.status})"
