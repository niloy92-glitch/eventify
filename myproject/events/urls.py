from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("client/my-events/", views.client_my_events_view, name="client_my_events"),
    path("client/events/<int:event_id>/", views.client_event_detail_view, name="client_event_detail"),
    path("client/events/create/", views.client_event_create_view, name="client_event_create"),
    path("client/events/<int:event_id>/update/", views.client_event_update_view, name="client_event_update"),
    path("client/events/<int:event_id>/payment/", views.client_event_payment_view, name="client_event_payment"),
    path("client/events/<int:event_id>/delete/", views.client_event_delete_view, name="client_event_delete"),
    path("vendor/events/", views.vendor_events_view, name="vendor_events"),
    path("vendor/booking-requests/", views.vendor_booking_requests_view, name="vendor_booking_requests"),
]
