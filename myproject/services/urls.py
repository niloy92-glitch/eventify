from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("vendor/", views.vendor_service_list, name="vendor_services"),
    path(
        "vendor/create/",
        views.vendor_service_create,
        name="vendor_service_create",
    ),
    path(
        "vendor/<int:pk>/",
        views.vendor_service_profile,
        name="vendor_service_profile",
    ),
    path(
        "vendor/<int:pk>/edit/",
        views.vendor_service_edit,
        name="vendor_service_edit",
    ),
    path(
        "vendor/<int:pk>/delete/",
        views.vendor_service_delete,
        name="vendor_service_delete",
    ),
    path("home/", views.services_home, name="services_home"),
    path("book/", views.book_service_request, name="book_service_request"),
    path(
        "vendor/booking-request/update/",
        views.vendor_booking_request_update,
        name="vendor_booking_request_update",
    ),
    path(
        "<int:service_id>/rate/",
        views.service_rate_view,
        name="service_rate",
    ),
    path(
        "<int:service_id>/rating/",
        views.service_rating_view,
        name="service_rating",
    ),
]
