from django.contrib import admin

from .models import Event, EventServiceBooking


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ("title", "client", "event_date", "has_own_venue", "payment_method", "created_at")
	list_filter = ("has_own_venue", "payment_method", "event_date", "created_at")
	search_fields = ("title", "client__email", "venue_name", "venue_address")
	ordering = ("-event_date",)


@admin.register(EventServiceBooking)
class EventServiceBookingAdmin(admin.ModelAdmin):
	list_display = ("event", "service", "vendor", "status", "requested_date", "created_at")
	list_filter = ("status", "requested_date", "created_at")
	search_fields = ("event__title", "service__name", "vendor__email", "vendor__company_name")
	ordering = ("-created_at",)
