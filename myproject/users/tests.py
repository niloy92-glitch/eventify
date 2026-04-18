import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
		self.assertEqual(response.json()["redirect_url"], "/client/")

		landing = self.client.get(response.json()["redirect_url"], follow=True)
		self.assertContains(landing, "hello Ava Stone, client!")

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
		self.assertEqual(response.json()["redirect_url"], "/vendor/")

		landing = self.client.get(response.json()["redirect_url"], follow=True)
		self.assertContains(landing, "hello Bright Events, vendor!")

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
		self.assertEqual(response.json()["redirect_url"], "/users/dashboard/admin/")

		user = User.objects.get(email="admin@example.com")
		self.assertEqual(user.role, "admin")
		self.assertEqual(user.referral_code, "eventify")
		self.assertFalse(user.is_staff)

		landing = self.client.get(response.json()["redirect_url"])
		self.assertContains(landing, "hello Maya Patel, admin!")

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
