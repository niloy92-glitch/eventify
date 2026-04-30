from django.contrib import admin

from .models import ApprovalRequest, Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
	list_display = ("name", "vendor", "service_type", "price", "is_approved", "created_at")
	list_filter = ("service_type", "is_approved", "created_at")
	search_fields = ("name", "description", "vendor__email", "vendor__first_name", "vendor__last_name", "vendor__company_name")
	ordering = ("-created_at",)


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
	list_display = ("request_type", "service", "vendor", "status", "created_at")
	list_filter = ("request_type", "status", "created_at")
	search_fields = ("service__name", "vendor__email", "vendor__first_name", "vendor__last_name", "vendor__company_name")
	ordering = ("-created_at",)