from django.contrib.auth.models import BaseUserManager


class EventUserManager(BaseUserManager):
	def create_user(self, email, password=None, role="client", **extra_fields):
		if not email:
			raise ValueError("Users must have an email address.")
		email = self.normalize_email(email)
		user = self.model(email=email, role=role, **extra_fields)
		if password:
			user.set_password(password)
		else:
			user.set_unusable_password()
		user.save(using=self._db)
		return user

	def create_superuser(self, email, password, **extra_fields):
		extra_fields.setdefault("role", "admin")
		extra_fields.setdefault("is_staff", True)
		extra_fields.setdefault("is_superuser", True)
		extra_fields.setdefault("first_name", "Super")
		extra_fields.setdefault("last_name", "User")
		extra_fields.setdefault("referral_code", "SYSTEM")

		if extra_fields.get("is_staff") is not True:
			raise ValueError("Superuser must have is_staff=True.")
		if extra_fields.get("is_superuser") is not True:
			raise ValueError("Superuser must have is_superuser=True.")

		return self.create_user(email, password, **extra_fields)
