import json

from django import forms
from django.contrib.auth import get_user_model

from .services import ADMIN_REFERRAL_CODE, normalize_role


User = get_user_model()


class JSONPayloadForm(forms.Form):
    @classmethod
    def from_request_body(cls, body: bytes):
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return cls(payload)


class LoginJSONForm(JSONPayloadForm):
    role = forms.CharField(required=False)
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)
    remember = forms.BooleanField(required=False)

    def clean_role(self):
        return normalize_role(self.cleaned_data.get("role"))

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class RegisterJSONForm(JSONPayloadForm):
    role = forms.CharField(required=False)
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)
    confirm_password = forms.CharField(required=True)

    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    company_name = forms.CharField(required=False)
    referral_code = forms.CharField(required=False)

    def clean_role(self):
        return normalize_role(self.cleaned_data.get("role"))

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_first_name(self):
        return self.cleaned_data.get("first_name", "").strip()

    def clean_last_name(self):
        return self.cleaned_data.get("last_name", "").strip()

    def clean_company_name(self):
        return self.cleaned_data.get("company_name", "").strip()

    def clean_referral_code(self):
        return self.cleaned_data.get("referral_code", "").strip() or ADMIN_REFERRAL_CODE

    def clean(self):
        cleaned_data = super().clean()
        role = normalize_role(cleaned_data.get("role"))
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        email = cleaned_data.get("email")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error("email", "An account with that email already exists.")

        if role in {"client", "admin"}:
            if not cleaned_data.get("first_name"):
                self.add_error("first_name", "First name is required.")
            if not cleaned_data.get("last_name"):
                self.add_error("last_name", "Last name is required.")

        if role == "vendor" and not cleaned_data.get("company_name"):
            self.add_error("company_name", "Company name is required.")

        if role == "admin":
            referral_code = cleaned_data.get("referral_code", "")
            if referral_code.lower() != ADMIN_REFERRAL_CODE:
                self.add_error("referral_code", "Invalid referral code.")

        cleaned_data["role"] = role
        return cleaned_data
