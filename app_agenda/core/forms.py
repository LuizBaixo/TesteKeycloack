from django import forms
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("title", "scheduled_at", "color", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex.: Reunião de projeto"}),
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Detalhes opcionais"}),
        }
