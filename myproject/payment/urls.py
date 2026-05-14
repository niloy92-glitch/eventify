from django.urls import path

from . import views

app_name = "payment"

urlpatterns = [
    path("client/transactions/", views.client_transactions_view, name="client_transactions"),
    path("vendor/transactions/", views.vendor_transactions_view, name="vendor_transactions"),
    path("admin/transactions/", views.admin_transactions_view, name="admin_transactions"),
    path("events/<int:event_id>/checkout/", views.client_event_checkout_view, name="client_event_checkout"),
]
