import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0002_extractedrow_has_correction"),
        ("deposits", "0002_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="upload",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="uploadimage",
                    name="upload",
                    field=models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="image",
                        to="ingestion.upload",
                    ),
                ),
                migrations.AlterField(
                    model_name="extraction",
                    name="upload",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extractions",
                        to="ingestion.upload",
                    ),
                ),
                migrations.AlterField(
                    model_name="extractedrow",
                    name="upload",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rows",
                        to="ingestion.upload",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE ingestion_upload DROP CONSTRAINT IF EXISTS ingestion_upload_pkey CASCADE;
                    ALTER TABLE ingestion_upload DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE ingestion_upload ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();

                    ALTER TABLE ingestion_uploadimage ALTER COLUMN upload_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_extraction ALTER COLUMN upload_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_extractedrow ALTER COLUMN upload_id TYPE uuid USING NULL;
                    ALTER TABLE deposits_deposit ALTER COLUMN upload_id TYPE uuid USING NULL;

                    ALTER TABLE ingestion_uploadimage ADD CONSTRAINT ingestion_uploadimage_upload_id_fk FOREIGN KEY (upload_id) REFERENCES ingestion_upload(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE ingestion_extraction ADD CONSTRAINT ingestion_extraction_upload_id_fk FOREIGN KEY (upload_id) REFERENCES ingestion_upload(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE ingestion_extractedrow ADD CONSTRAINT ingestion_extractedrow_upload_id_fk FOREIGN KEY (upload_id) REFERENCES ingestion_upload(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE deposits_deposit ADD CONSTRAINT deposits_deposit_upload_id_fk FOREIGN KEY (upload_id) REFERENCES ingestion_upload(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
                    """,
                    reverse_sql="""
                    """,
                ),
            ],
        ),
    ]
