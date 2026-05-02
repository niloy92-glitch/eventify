from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from events.models import EventServiceBooking

class Conversation(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_conversations")
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("client", "vendor")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Chat between {self.client} and {self.vendor}"

    @property
    def is_locked(self):
        # Messaging is unlocked if there is at least one approved booking
        # where the event date is less than 7 days in the past (or in the future).
        cutoff_date = timezone.localdate() - timedelta(days=7)
        has_active_booking = EventServiceBooking.objects.filter(
            event__client=self.client,
            service__vendor=self.vendor,
            status__in=["approved", "pending"],
            event__event_date__gte=cutoff_date
        ).exists()
        return not has_active_booking

    def active_bookings(self):
        # Get bookings that justify the unlock and show context
        cutoff_date = timezone.localdate() - timedelta(days=7)
        return EventServiceBooking.objects.filter(
            event__client=self.client,
            service__vendor=self.vendor,
            status__in=["approved", "pending"],
            event__event_date__gte=cutoff_date
        ).select_related("event", "service")

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages", null=True, blank=True)
    content = models.TextField()
    is_system = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender} at {self.created_at}"
