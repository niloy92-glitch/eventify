from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.conf import settings
from django.db import models
from django.utils import timezone

from .managers import EventUserManager


class RoleChoices(models.TextChoices):
    CLIENT = "client", "Client"
    VENDOR = "vendor", "Vendor"
    ADMIN = "admin", "Admin"


class ApprovalStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    ALLOWED = "allowed", "Allowed"
    REJECTED = "rejected", "Rejected"


class EventUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20, choices=RoleChoices.choices, default=RoleChoices.CLIENT
    )
    vendor_approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatusChoices.choices,
        default=ApprovalStatusChoices.ALLOWED,
    )

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    referral_code = models.CharField(max_length=100, blank=True)
    email_verified = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = EventUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def get_full_name(self):
        if self.role == RoleChoices.VENDOR and self.company_name:
            return self.company_name
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        if self.role == RoleChoices.VENDOR and self.company_name:
            return self.company_name
        if self.first_name:
            return self.first_name
        return self.email

    def __str__(self):
        return self.get_full_name()


class NotificationCategoryChoices(models.TextChoices):
    MESSAGE = "message", "Message"
    REQUEST = "request", "Request"
    APPROVAL = "approval", "Approval"
    VERIFICATION = "verification", "Verification"
    SYSTEM = "system", "System"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=NotificationCategoryChoices.choices,
        default=NotificationCategoryChoices.SYSTEM,
    )
    link_url = models.CharField(max_length=255, blank=True)
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
