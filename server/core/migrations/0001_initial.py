from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BankSampah",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("city", models.CharField(blank=True, max_length=255, null=True)),
                ("is_demo", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Nasabah",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("normalized_name", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("bank_sampah", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="nasabah", to="core.banksampah")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("bank_sampah", "normalized_name"), name="unique_nasabah_per_bank")
                ],
            },
        ),
    ]
