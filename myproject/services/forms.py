from django import forms
from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "service_type", "price"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-field-input",
                "placeholder": "Service name"
            }),
            "service_type": forms.Select(attrs={
                "class": "form-field-input"
            }),
            "price": forms.NumberInput(attrs={
                "class": "form-field-input",
                "placeholder": "0.00",
                "step": "0.01"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-field-input",
                "rows": 5,
                "placeholder": "Describe your service in detail..."
            }),
        }
