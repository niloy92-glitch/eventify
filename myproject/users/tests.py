import json

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


User = get_user_model()


class AuthFlowTests(TestCase):
	def post_json(self, url_name, payload):
		return self.client.post(
			reverse(url_name),
			data=json.dumps(payload),
			content_type="application/json",
		)

	def test_client_registration_redirects_to_client_landing(self):
		response = self.post_json(
			"users:register_api",
			{
				"role": "client",
				"first_name": "Ava",
				"last_name": "Stone",
				"email": "ava@example.com",
				"password": "secret12345",
				"confirm_password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn("/users/login/", response.json()["redirect_url"])

		user = User.objects.get(email="ava@example.com")
		self.assertFalse(user.email_verified)

	def test_vendor_registration_uses_company_name(self):
		response = self.post_json(
			"users:register_api",
			{
				"role": "vendor",
				"company_name": "Bright Events",
				"email": "vendor@example.com",
				"password": "secret12345",
				"confirm_password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn("/users/login/", response.json()["redirect_url"])

		user = User.objects.get(email="vendor@example.com")
		self.assertEqual(user.company_name, "Bright Events")
		self.assertFalse(user.email_verified)

	def test_admin_registration_accepts_default_referral_code(self):
		response = self.post_json(
			"users:register_api",
			{
				"role": "admin",
				"first_name": "Maya",
				"last_name": "Patel",
				"email": "admin@example.com",
				"password": "secret12345",
				"confirm_password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn("/users/login/", response.json()["redirect_url"])

		user = User.objects.get(email="admin@example.com")
		self.assertEqual(user.role, "admin")
		self.assertEqual(user.referral_code, "eventify")
		self.assertFalse(user.is_staff)
		self.assertFalse(user.email_verified)

	def test_unverified_user_cannot_login(self):
		User.objects.create_user(
			email="newuser@example.com",
			password="secret12345",
			role="client",
			email_verified=False,
		)

		response = self.post_json(
			"users:login_api",
			{
				"role": "client",
				"email": "newuser@example.com",
				"password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 403)
		self.assertIn("verify", response.json()["message"].lower())

	def test_django_admin_accounts_cannot_login_through_eventify(self):
		User.objects.create_superuser(email="staff@example.com", password="secret12345")

		response = self.post_json(
			"users:login_api",
			{
				"role": "admin",
				"email": "staff@example.com",
				"password": "secret12345",
			},
		)

		self.assertEqual(response.status_code, 403)
		self.assertFalse(response.json()["ok"])
		self.assertIn("Django admin", response.json()["message"])

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
