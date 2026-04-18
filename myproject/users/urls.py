from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.root_redirect, name="root"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("api/login/", views.login_api, name="login_api"),
    path("api/register/", views.register_api, name="register_api"),
    path("dashboard/<str:role>/", views.dashboard, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),
]
