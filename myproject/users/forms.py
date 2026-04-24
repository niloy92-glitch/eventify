from django import forms
from django.contrib.auth import get_user_model

from .services import ADMIN_REFERRAL_CODE, normalize_role


User = get_user_model()


def _bool_from_post(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class LoginForm(forms.Form):
    role = forms.CharField(required=False)
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)
    remember = forms.BooleanField(required=False)

    @classmethod
    def from_post_data(cls, post_data, role: str):
        payload = {
            "role": role,
            "email": str(post_data.get("email", "")).strip(),
            "password": str(post_data.get("password", "")),
            "remember": _bool_from_post(post_data.get("remember")),
        }
        return cls(payload)

    def clean_role(self):
        return normalize_role(self.cleaned_data.get("role"))

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class RegisterForm(forms.Form):
    role = forms.CharField(required=False)
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True)
    confirm_password = forms.CharField(required=True)

    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    company_name = forms.CharField(required=False)
    referral_code = forms.CharField(required=False)

    @classmethod
    def from_post_data(cls, post_data, role: str):
        payload = {
            "role": role,
            "email": "",
            "password": "",
            "confirm_password": "",
            "first_name": "",
            "last_name": "",
            "company_name": "",
            "referral_code": "",
        }

        if role == "client":
            payload.update(
                {
                    "first_name": str(post_data.get("client_first_name", "")).strip(),
                    "last_name": str(post_data.get("client_last_name", "")).strip(),
                    "email": str(post_data.get("client_email", "")).strip(),
                    "password": str(post_data.get("client_password", "")),
                    "confirm_password": str(post_data.get("client_confirm_password", "")),
                }
            )
            return cls(payload)

        if role == "vendor":
            payload.update(
                {
                    "company_name": str(post_data.get("vendor_company_name", "")).strip(),
                    "email": str(post_data.get("vendor_email", "")).strip(),
                    "password": str(post_data.get("vendor_password", "")),
                    "confirm_password": str(post_data.get("vendor_confirm_password", "")),
                }
            )
            return cls(payload)

        payload.update(
            {
                "first_name": str(post_data.get("admin_first_name", "")).strip(),
                "last_name": str(post_data.get("admin_last_name", "")).strip(),
                "email": str(post_data.get("admin_email", "")).strip(),
                "password": str(post_data.get("admin_password", "")),
                "confirm_password": str(post_data.get("admin_confirm_password", "")),
                "referral_code": str(post_data.get("admin_referral_code", "")).strip(),
            }
        )
        return cls(payload)

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
        return self.cleaned_data.get("referral_code", "").strip()

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
            if not referral_code:
                self.add_error("referral_code", "Referral code is required.")
            elif referral_code.lower() != ADMIN_REFERRAL_CODE:
                self.add_error("referral_code", "Invalid referral code.")

        cleaned_data["role"] = role
        return cleaned_data
