import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0002_alter_user_id"),
        ("core", "0003_alter_models_to_uuid"),
        ("deposits", "0003_alter_deposit_auditlog_to_uuid"),
        ("ingestion", "0003_alter_upload_id"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="upload",
                    name="bank_sampah",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="uploads",
                        to="core.banksampah",
                    ),
                ),
                migrations.AlterField(
                    model_name="upload",
                    name="created_by",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="uploads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name="uploadimage",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="extraction",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="extractedrow",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="extractedrow",
                    name="extraction",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rows",
                        to="ingestion.extraction",
                    ),
                ),
                migrations.AlterField(
                    model_name="extractedrow",
                    name="nasabah",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="extracted_rows",
                        to="core.nasabah",
                    ),
                ),
                migrations.AlterField(
                    model_name="extractedrow",
                    name="waste_type",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="extracted_rows",
                        to="core.wastetype",
                    ),
                ),
                migrations.AlterField(
                    model_name="extractedrow",
                    name="deposit",
                    field=models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="extracted_row",
                        to="deposits.deposit",
                    ),
                ),
                migrations.AlterField(
                    model_name="providercache",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE ingestion_upload ALTER COLUMN bank_sampah_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_upload ALTER COLUMN created_by_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_upload ADD CONSTRAINT ingestion_upload_bank_sampah_id_fk FOREIGN KEY (bank_sampah_id) REFERENCES core_banksampah(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE ingestion_upload ADD CONSTRAINT ingestion_upload_created_by_id_fk FOREIGN KEY (created_by_id) REFERENCES accounts_user(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE ingestion_uploadimage DROP CONSTRAINT IF EXISTS ingestion_uploadimage_pkey CASCADE;
                    ALTER TABLE ingestion_uploadimage DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE ingestion_uploadimage ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();

                    ALTER TABLE ingestion_extraction DROP CONSTRAINT IF EXISTS ingestion_extraction_pkey CASCADE;
                    ALTER TABLE ingestion_extraction DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE ingestion_extraction ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();

                    ALTER TABLE ingestion_extractedrow DROP CONSTRAINT IF EXISTS ingestion_extractedrow_pkey CASCADE;
                    ALTER TABLE ingestion_extractedrow DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE ingestion_extractedrow ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    ALTER TABLE ingestion_extractedrow ALTER COLUMN extraction_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_extractedrow ALTER COLUMN nasabah_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_extractedrow ALTER COLUMN waste_type_id TYPE uuid USING NULL;
                    ALTER TABLE ingestion_extractedrow ALTER COLUMN deposit_id TYPE uuid USING NULL;

                    ALTER TABLE ingestion_extractedrow ADD CONSTRAINT ingestion_extractedrow_extraction_id_fk FOREIGN KEY (extraction_id) REFERENCES ingestion_extraction(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE ingestion_extractedrow ADD CONSTRAINT ingestion_extractedrow_nasabah_id_fk FOREIGN KEY (nasabah_id) REFERENCES core_nasabah(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE ingestion_extractedrow ADD CONSTRAINT ingestion_extractedrow_waste_type_id_fk FOREIGN KEY (waste_type_id) REFERENCES core_wastetype(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE ingestion_extractedrow ADD CONSTRAINT ingestion_extractedrow_deposit_id_fk FOREIGN KEY (deposit_id) REFERENCES deposits_deposit(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE ingestion_providercache DROP CONSTRAINT IF EXISTS ingestion_providercache_pkey CASCADE;
                    ALTER TABLE ingestion_providercache DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE ingestion_providercache ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    """,
                    reverse_sql="""
                    """,
                ),
            ],
        ),
    ]
