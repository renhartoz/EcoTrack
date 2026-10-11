import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_wastetype_wastetypealias"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="banksampah",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="nasabah",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="wastetype",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="wastetypealias",
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
                    TRUNCATE TABLE
                        deposits_deposit,
                        deposits_auditlog,
                        ingestion_extractedrow,
                        ingestion_extraction,
                        ingestion_uploadimage,
                        ingestion_upload,
                        accounts_user_groups,
                        accounts_user_user_permissions,
                        token_blacklist_outstandingtoken,
                        accounts_user,
                        core_nasabah,
                        core_wastetypealias,
                        core_wastetype,
                        core_banksampah
                    CASCADE;

                    ALTER TABLE core_banksampah DROP CONSTRAINT IF EXISTS core_banksampah_pkey CASCADE;
                    ALTER TABLE core_banksampah DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE core_banksampah ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();

                    ALTER TABLE core_wastetype DROP CONSTRAINT IF EXISTS core_wastetype_pkey CASCADE;
                    ALTER TABLE core_wastetype DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE core_wastetype ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();

                    ALTER TABLE core_nasabah DROP CONSTRAINT IF EXISTS core_nasabah_pkey CASCADE;
                    ALTER TABLE core_nasabah DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE core_nasabah ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    ALTER TABLE core_nasabah ALTER COLUMN bank_sampah_id TYPE uuid USING NULL;
                    ALTER TABLE core_nasabah ADD CONSTRAINT core_nasabah_bank_sampah_id_fk FOREIGN KEY (bank_sampah_id) REFERENCES core_banksampah(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE core_wastetypealias DROP CONSTRAINT IF EXISTS core_wastetypealias_pkey CASCADE;
                    ALTER TABLE core_wastetypealias DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE core_wastetypealias ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    ALTER TABLE core_wastetypealias ALTER COLUMN waste_type_id TYPE uuid USING NULL;
                    ALTER TABLE core_wastetypealias ADD CONSTRAINT core_wastetypealias_waste_type_id_fk FOREIGN KEY (waste_type_id) REFERENCES core_wastetype(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    """,
                    reverse_sql="""
                    """,
                ),
            ],
        ),
    ]
