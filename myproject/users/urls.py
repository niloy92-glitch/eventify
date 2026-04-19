from django.contrib.auth import views as auth_views
from django.conf import settings
from django.urls import path
from django.urls import reverse_lazy

from . import views

app_name = "users"

urlpatterns = [
    path("", views.root_redirect, name="root"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("auth/google/start/", views.google_oauth_start, name="google_oauth_start"),
    path("auth/google/callback/", views.google_oauth_callback, name="google_oauth_callback"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("api/login/", views.login_api, name="login_api"),
    path("api/register/", views.register_api, name="register_api"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="users/password_reset_form.html",
            email_template_name="users/password_reset_email.txt",
            html_email_template_name="users/password_reset_email.html",
            subject_template_name="users/password_reset_subject.txt",
            extra_email_context={"brand_name": settings.EMAIL_BRAND_NAME},
            success_url=reverse_lazy("users:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("dashboard/<str:role>/", views.dashboard, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),
]
