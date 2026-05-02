from django import forms
from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "event_date", "venue_name", "venue_address", "payment_method", "has_own_venue", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-field-input", "id": "client-event-title", "placeholder": "Event title"}),
            "event_date": forms.DateInput(attrs={"class": "form-field-input", "id": "client-event-date", "type": "date"}),
            "venue_name": forms.TextInput(attrs={"class": "form-field-input", "id": "client-event-venue-name", "placeholder": "Venue name"}),
            "venue_address": forms.Textarea(attrs={"class": "form-field-input", "id": "client-event-venue-address", "rows": 3, "placeholder": "Venue address or notes"}),
            "payment_method": forms.Select(attrs={"class": "form-field-input", "id": "client-event-payment-method"}),
            "has_own_venue": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "client-event-own-venue"}),
            "notes": forms.Textarea(attrs={"class": "form-field-input", "id": "client-event-notes", "rows": 4, "placeholder": "Optional event notes"}),
        }


class EventPaymentForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=Event.PAYMENT_METHODS,
        widget=forms.Select(attrs={"class": "form-field-input"}),
    )
