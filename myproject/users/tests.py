from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


User = get_user_model()


class AuthFlowTests(TestCase):
	def test_client_registration_redirects_to_client_landing(self):
		response = self.client.post(
			reverse("users:register"),
			{
				"role": "client",
				"client_first_name": "Ava",
				"client_last_name": "Stone",
				"client_email": "ava@example.com",
				"client_password": "secret12345",
				"client_confirm_password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertIn("/users/login/", response["Location"])

		user = User.objects.get(email="ava@example.com")
		self.assertFalse(user.email_verified)

	def test_vendor_registration_uses_company_name(self):
		response = self.client.post(
			reverse("users:register"),
			{
				"role": "vendor",
				"vendor_company_name": "Bright Events",
				"vendor_email": "vendor@example.com",
				"vendor_password": "secret12345",
				"vendor_confirm_password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertIn("/users/login/", response["Location"])

		user = User.objects.get(email="vendor@example.com")
		self.assertEqual(user.company_name, "Bright Events")
		self.assertFalse(user.email_verified)

	def test_admin_registration_requires_valid_referral_code(self):
		response = self.client.post(
			reverse("users:register"),
			{
				"role": "admin",
				"admin_first_name": "Maya",
				"admin_last_name": "Patel",
				"admin_email": "admin@example.com",
				"admin_password": "secret12345",
				"admin_confirm_password": "secret12345",
				"admin_referral_code": "eventify",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertIn("/users/login/", response["Location"])

		user = User.objects.get(email="admin@example.com")
		self.assertEqual(user.role, "admin")
		self.assertEqual(user.referral_code, "eventify")
		self.assertFalse(user.is_staff)
		self.assertFalse(user.email_verified)

	def test_admin_registration_fails_without_referral_code(self):
		response = self.client.post(
			reverse("users:register"),
			{
				"role": "admin",
				"admin_first_name": "Maya",
				"admin_last_name": "Patel",
				"admin_email": "admin-missing-ref@example.com",
				"admin_password": "secret12345",
				"admin_confirm_password": "secret12345",
				"admin_referral_code": "",
			},
		)

		self.assertEqual(response.status_code, 403)
		self.assertContains(response, "Referral code is required", status_code=403)
		self.assertFalse(User.objects.filter(email="admin-missing-ref@example.com").exists())

	def test_unverified_user_cannot_login(self):
		User.objects.create_user(
			email="newuser@example.com",
			password="secret12345",
			role="client",
			email_verified=False,
		)

		response = self.client.post(
			reverse("users:login"),
			{
				"role": "client",
				"email": "newuser@example.com",
				"password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 403)
		self.assertContains(response, "verify", status_code=403)

	def test_django_admin_accounts_cannot_login_through_eventify(self):
		User.objects.create_superuser(email="staff@example.com", password="secret12345")

		response = self.client.post(
			reverse("users:login"),
			{
				"role": "admin",
				"email": "staff@example.com",
				"password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 403)
		self.assertContains(response, "Django admin", status_code=403)

	def test_verify_email_token_marks_user_as_verified(self):
		user = User.objects.create_user(
			email="verifyme@example.com",
			password="secret12345",
			role="client",
			email_verified=False,
		)

		uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
		token = default_token_generator.make_token(user)
		response = self.client.get(reverse("users:verify_email", args=[uidb64, token]))

		self.assertEqual(response.status_code, 200)
		user.refresh_from_db()
		self.assertTrue(user.email_verified)
		self.assertContains(response, "Email Verified")

	def test_password_reset_complete_template_has_login_redirect_target(self):
		response = self.client.get(reverse("users:password_reset_complete"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, reverse("users:login"))
		self.assertContains(response, "Password reset successful")

	def test_google_oauth_callback_handles_bad_state(self):
		response = self.client.get(reverse("users:google_oauth_callback"), {"state": "invalid", "code": "abc"})
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("users:login"), response["Location"])

	def test_google_oauth_callback_handles_error_query(self):
		response = self.client.get(reverse("users:google_oauth_callback"), {"error": "access_denied"})
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("users:login"), response["Location"])
