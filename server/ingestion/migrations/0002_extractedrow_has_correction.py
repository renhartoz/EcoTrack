from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="extractedrow",
            name="has_correction",
            field=models.BooleanField(default=False),
        ),
    ]
