from django.conf import settings
from django.db import models


class Appointment(models.Model):
    COLOR_CHOICES = [
        ("#2563eb", "Azul"),
        ("#7c3aed", "Roxo"),
        ("#db2777", "Rosa"),
        ("#dc2626", "Vermelho"),
        ("#ea580c", "Laranja"),
        ("#16a34a", "Verde"),
    ]
    title = models.CharField("título", max_length=120)
    scheduled_at = models.DateTimeField("data e hora")
    notes = models.TextField("observações", blank=True)
    color = models.CharField("cor", max_length=7, choices=COLOR_CHOICES, default="#2563eb")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return self.title
