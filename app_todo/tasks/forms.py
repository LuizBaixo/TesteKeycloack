from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "due_date")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex.: Enviar proposta"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
