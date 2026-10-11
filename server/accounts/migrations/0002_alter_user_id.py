import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("core", "0003_alter_models_to_uuid"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="user",
                    name="bank_sampah",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="users",
                        to="core.banksampah",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE accounts_user DROP CONSTRAINT IF EXISTS accounts_user_pkey CASCADE;
                    ALTER TABLE accounts_user DROP COLUMN IF EXISTS id CASCADE;
                    ALTER TABLE accounts_user ADD COLUMN id uuid PRIMARY KEY DEFAULT gen_random_uuid();
                    ALTER TABLE accounts_user ALTER COLUMN bank_sampah_id TYPE uuid USING NULL;
                    ALTER TABLE accounts_user ADD CONSTRAINT accounts_user_bank_sampah_id_fk FOREIGN KEY (bank_sampah_id) REFERENCES core_banksampah(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE accounts_user_groups ALTER COLUMN user_id TYPE uuid USING NULL;
                    ALTER TABLE accounts_user_groups ADD CONSTRAINT accounts_user_groups_user_id_fk FOREIGN KEY (user_id) REFERENCES accounts_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE accounts_user_user_permissions ALTER COLUMN user_id TYPE uuid USING NULL;
                    ALTER TABLE accounts_user_user_permissions ADD CONSTRAINT accounts_user_user_permissions_user_id_fk FOREIGN KEY (user_id) REFERENCES accounts_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

                    ALTER TABLE token_blacklist_outstandingtoken ALTER COLUMN user_id TYPE uuid USING NULL;
                    ALTER TABLE token_blacklist_outstandingtoken ADD CONSTRAINT token_blacklist_outstandingtoken_user_id_fk FOREIGN KEY (user_id) REFERENCES accounts_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
                    """,
                    reverse_sql="""
                    """,
                ),
            ],
        ),
    ]
