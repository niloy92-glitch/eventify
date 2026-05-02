from django.urls import path
from . import views
from events import views as event_views

app_name = "services"

urlpatterns = [
    path("vendor/", views.vendor_service_list, name="vendor_services"),
    path("vendor/create/", views.vendor_service_create, name="vendor_service_create"),
    path("vendor/<int:pk>/edit/", views.vendor_service_edit, name="vendor_service_edit"),
    path("vendor/<int:pk>/delete/", views.vendor_service_delete, name="vendor_service_delete"),
    path("home/", views.services_home, name="services_home"),
    path("book/", event_views.book_service_request, name="book_service_request"),
    path("vendor/booking-request/update/", event_views.vendor_booking_request_update, name="vendor_booking_request_update"),
]
