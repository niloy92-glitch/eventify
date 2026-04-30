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
    path("resend-verification-email/", views.resend_verification_email_view, name="resend_verification_email"),
    path("auth/google/start/", views.google_oauth_start, name="google_oauth_start"),
    path("auth/google/callback/", views.google_oauth_callback, name="google_oauth_callback"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset_form.html",
            email_template_name="password_reset_email.txt",
            html_email_template_name="password_reset_email.html",
            subject_template_name="password_reset_subject.txt",
            extra_email_context={"brand_name": settings.EMAIL_BRAND_NAME},
            success_url=reverse_lazy("users:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("client/dashboard/", views.client_dashboard_view, name="client_dashboard"),
    path("client/my-events/", views.client_my_events_view, name="client_my_events"),
    path("client/messages/", views.client_messages_view, name="client_messages"),
    path("client/profile/", views.client_profile_view, name="client_profile"),
    path("client/profile/update/", views.client_profile_update_view, name="client_profile_update"),
    path("client/profile/delete/", views.client_delete_account_view, name="client_delete_account"),
    path("vendor/dashboard/", views.vendor_dashboard_view, name="vendor_dashboard"),
    path("vendor/services/", views.vendor_services_view, name="vendor_services"),
    path("vendor/events/", views.vendor_events_view, name="vendor_events"),
    path("vendor/messages/", views.vendor_messages_view, name="vendor_messages"),
    path("vendor/profile/", views.vendor_profile_view, name="vendor_profile"),
    path("vendor/profile/update/", views.vendor_profile_update_view, name="vendor_profile_update"),
    path("vendor/profile/delete/", views.vendor_delete_account_view, name="vendor_delete_account"),
    path("dashboard/<str:role>/", views.dashboard, name="dashboard"),
    path("admin/dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("admin/users/", views.admin_users_view, name="admin_users"),
    path("admin/users/<int:user_id>/update/", views.admin_user_update_view, name="admin_user_update"),
    path("admin/users/<int:user_id>/delete/", views.admin_user_delete_view, name="admin_user_delete"),
    path("admin/approvals/", views.admin_approvals_view, name="admin_approvals"),
    path("admin/approvals/update/", views.admin_approval_update_view, name="admin_approval_update"),
    path("admin/activity-logs/", views.admin_activity_logs_view, name="admin_activity_logs"),
    path("admin/profile/", views.admin_profile_view, name="admin_profile"),
    path("logout/", views.logout_view, name="logout"),
]
