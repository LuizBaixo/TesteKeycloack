from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="appointment",
            name="color",
            field=models.CharField(choices=[("#2563eb", "Azul"), ("#7c3aed", "Roxo"), ("#db2777", "Rosa"), ("#dc2626", "Vermelho"), ("#ea580c", "Laranja"), ("#16a34a", "Verde")], default="#2563eb", max_length=7, verbose_name="cor"),
        ),
    ]
