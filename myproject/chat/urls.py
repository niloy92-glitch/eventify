from django.urls import path
from chat import views

app_name = "chat"

urlpatterns = [
    path("client/messages/", views.client_chat_view, name="client_chat_list"),
    path("client/messages/<int:conversation_id>/", views.client_chat_view, name="client_chat_detail"),
    path("vendor/messages/", views.vendor_chat_view, name="vendor_chat_list"),
    path("vendor/messages/<int:conversation_id>/", views.vendor_chat_view, name="vendor_chat_detail"),
]
