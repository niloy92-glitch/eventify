from django import forms

from .models import PaymentMethod


class VendorPaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ["provider", "account_name", "account_number", "is_active"]
        widgets = {
            "provider": forms.Select(attrs={"class": "input"}),
            "account_name": forms.TextInput(attrs={"class": "input", "placeholder": "Account holder name"}),
            "account_number": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. 017XXXXXXXX"}),
            "is_active": forms.CheckboxInput(attrs={"class": "input-check"}),
        }
