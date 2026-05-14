from django.db import models
from django.conf import settings


class Service(models.Model):
    SERVICE_TYPES = [
        ("catering", "Catering"),
        ("photography", "Photography"),
        ("decoration", "Decoration"),
        ("music", "Music"),
        ("venue", "Venue"),
        ("other", "Other"),
    ]

    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    service_type = models.CharField(
        max_length=40, choices=SERVICE_TYPES, default="other"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.vendor})"


class ServiceAvailabilitySlot(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="availability_slots"
    )
    available_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["available_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "available_date"],
                name="unique_service_availability_slot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service} @ {self.available_date}"


class ApprovalRequest(models.Model):
    REQUEST_TYPES = [
        ("service", "Service"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("allowed", "Allowed"),
        ("rejected", "Rejected"),
    ]

    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES)
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="approval_requests"
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.request_type}:{self.service_id} ({self.status})"


class ServiceRating(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="ratings"
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_ratings",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="service_ratings",
    )
    stars = models.IntegerField()  # 1-5 stars
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_ratings",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "client", "event"],
                name="unique_service_rating_per_client_per_event",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service.name} - {self.stars}★ by {self.client.email}"
