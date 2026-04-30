from django.db import models
from django.conf import settings


class Service(models.Model):
    SERVICE_TYPES = [
        ("catering", "Catering"),
        ("photography", "Photography"),
        ("decoration", "Decoration"),
        ("music", "Music"),
        ("other", "Other"),
    ]

    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    service_type = models.CharField(max_length=40, choices=SERVICE_TYPES, default="other")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.vendor})"


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
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="approval_requests")
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.request_type}:{self.service_id} ({self.status})"
