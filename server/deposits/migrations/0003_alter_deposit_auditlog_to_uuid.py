import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0002_alter_user_id"),
        ("core", "0003_alter_models_to_uuid"),
        ("deposits", "0002_initial"),
        ("ingestion", "0003_alter_upload_id"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="deposit",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="deposit",
                    name="bank_sampah",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deposits",
                        to="core.banksampah",
                    ),
                ),
                migrations.AlterField(
                    model_name="deposit",
                    name="nasabah",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deposits",
                        to="core.nasabah",
                    ),
                ),
                migrations.AlterField(
                    model_name="deposit",
                    name="waste_type",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deposits",
                        to="core.wastetype",
                    ),
                ),
                migrations.AlterField(
                    model_name="deposit",
                    name="created_by",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="deposits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name="auditlog",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="auditlog",
                    name="bank_sampah",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_logs",
                        to="core.banksampah",
                    ),
                ),
                migrations.AlterField(
                    model_name="auditlog",
                    name="actor",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name="auditlog",
                    name="entity_id",
                    field=models.UUIDField(),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE deposits_deposit DROP CONSTRAINT IF EXISTS deposits_deposit_pkey CASCADE;
                    ALTER TABLE deposits_deposit DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE deposits_deposit ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    ALTER TABLE deposits_deposit ALTER COLUMN bank_sampah_id TYPE uuid USING NULL;
                    ALTER TABLE deposits_deposit ALTER COLUMN nasabah_id TYPE uuid USING NULL;
                    ALTER TABLE deposits_deposit ALTER COLUMN waste_type_id TYPE uuid USING NULL;
                    ALTER TABLE deposits_deposit ALTER COLUMN created_by_id TYPE uuid USING NULL;

                    ALTER TABLE deposits_deposit ADD CONSTRAINT deposits_deposit_bank_sampah_id_fk FOREIGN KEY (bank_sampah_id) REFERENCES core_banksampah(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE deposits_deposit ADD CONSTRAINT deposits_deposit_nasabah_id_fk FOREIGN KEY (nasabah_id) REFERENCES core_nasabah(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE deposits_deposit ADD CONSTRAINT deposits_deposit_waste_type_id_fk FOREIGN KEY (waste_type_id) REFERENCES core_wastetype(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE deposits_deposit ADD CONSTRAINT deposits_deposit_created_by_id_fk FOREIGN KEY (created_by_id) REFERENCES accounts_user(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE deposits_auditlog DROP CONSTRAINT IF EXISTS deposits_auditlog_pkey CASCADE;
                    ALTER TABLE deposits_auditlog DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE deposits_auditlog ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    ALTER TABLE deposits_auditlog ALTER COLUMN bank_sampah_id TYPE uuid USING NULL;
                    ALTER TABLE deposits_auditlog ALTER COLUMN actor_id TYPE uuid USING NULL;
                    ALTER TABLE deposits_auditlog ALTER COLUMN entity_id TYPE uuid USING NULL;

                    ALTER TABLE deposits_auditlog ADD CONSTRAINT deposits_auditlog_bank_sampah_id_fk FOREIGN KEY (bank_sampah_id) REFERENCES core_banksampah(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    ALTER TABLE deposits_auditlog ADD CONSTRAINT deposits_auditlog_actor_id_fk FOREIGN KEY (actor_id) REFERENCES accounts_user(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
                    """,
                    reverse_sql="""
                    """,
                ),
            ],
        ),
    ]
