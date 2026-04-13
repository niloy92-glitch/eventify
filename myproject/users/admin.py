from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import EventUser, RoleChoices


@admin.register(EventUser)
class EventUserAdmin(UserAdmin):
	ordering = ("email",)
	list_display = ("email", "role", "is_staff", "is_active")
	search_fields = ("email", "first_name", "last_name", "company_name")
	list_filter = ("role", "is_staff", "is_superuser", "is_active")

	fieldsets = (
		(None, {"fields": ("email", "password")} ),
		(
			"Profile",
			{"fields": ("role", "first_name", "last_name", "company_name", "phone", "address", "referral_code")},
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


# @admin.register(Client)
# class ClientAdmin(admin.ModelAdmin):
# 	list_display = ("first_name", "last_name", "email", "role")
# 	search_fields = ("first_name", "last_name", "email")
# 	readonly_fields = tuple(field.name for field in Client._meta.fields)


# @admin.register(Vendor)
# class VendorAdmin(admin.ModelAdmin):
# 	list_display = ("company_name", "email", "role")
# 	search_fields = ("company_name", "email")
# 	readonly_fields = tuple(field.name for field in Vendor._meta.fields)


# @admin.register(AdminUser)
# class AdminUserAdmin(admin.ModelAdmin):
# 	list_display = ("first_name", "last_name", "email", "role", "referral_code")
# 	search_fields = ("first_name", "last_name", "email", "referral_code")
# 	readonly_fields = tuple(field.name for field in AdminUser._meta.fields)


admin.site.empty_value_display = "-"

# Register your models here.
