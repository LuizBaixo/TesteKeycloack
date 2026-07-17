from django.conf import settings
from django.db import models


class Task(models.Model):
    title = models.CharField("tarefa", max_length=160)
    due_date = models.DateField("prazo", blank=True, null=True)
    completed = models.BooleanField(default=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["completed", "due_date", "-created_at"]

    def __str__(self):
        return self.title
