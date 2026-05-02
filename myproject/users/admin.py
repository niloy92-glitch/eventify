from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import EventUser


@admin.register(EventUser)
class EventUserAdmin(UserAdmin):
	ordering = ("email",)
	list_display = ("email", "role", "email_verified", "is_staff", "is_active")
	search_fields = ("email", "email_verified", "first_name", "last_name", "company_name")
	list_filter = ("role", "vendor_approval_status", "is_staff", "is_superuser", "is_active")

	fieldsets = (
		(None, {"fields": ("email", "password")} ),
		(
			"Profile",
			{
				"fields": (
					"role",
					"vendor_approval_status",
                    "email_verified",
					"first_name",
					"last_name",
					"company_name",
					"phone",
					"address",
					"referral_code",
				)
			},
		),
		("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
		("Important dates", {"fields": ("last_login",)}),
	)

	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": ("email", "password1", "password2", "role", "first_name", "last_name", "referral_code"),
			},
		),
	)


admin.site.empty_value_display = "-"

# Register your models here.
