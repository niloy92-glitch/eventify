from django.contrib import admin

from .models import PaymentMethod, Payout, Transaction, TransactionServiceItem


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("vendor", "provider", "account_number", "is_active", "updated_at")
    search_fields = ("vendor__email", "vendor__company_name", "account_number")
    list_filter = ("provider", "is_active")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("tx_ref", "client", "event", "amount", "currency", "status", "created_at")
    search_fields = ("tx_ref", "client__email", "event__title")
    list_filter = ("status", "currency", "created_at")


@admin.register(TransactionServiceItem)
class TransactionServiceItemAdmin(admin.ModelAdmin):
    list_display = ("transaction", "service", "vendor", "service_total", "paid_amount")
    search_fields = ("transaction__tx_ref", "service__name", "vendor__email")
    list_filter = ("vendor",)


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("transaction", "vendor", "gross_amount", "status", "created_at")
    search_fields = ("transaction__tx_ref", "vendor__email")
    list_filter = ("status", "created_at")
