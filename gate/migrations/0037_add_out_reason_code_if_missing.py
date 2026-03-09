# Add out_reason_code to gate_gateentry if missing (fixes MySQL when 0036 was applied elsewhere)
from django.db import migrations, connection


def add_out_reason_code_if_missing(apps, schema_editor):
    with connection.cursor() as cursor:
        table = connection.ops.quote_name('gate_gateentry')
        # Check if column exists
        if connection.vendor == 'mysql':
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'gate_gateentry' AND COLUMN_NAME = 'out_reason_code'
            """)
            if cursor.fetchone()[0] > 0:
                return
            cursor.execute("ALTER TABLE gate_gateentry ADD COLUMN out_reason_code VARCHAR(32) NOT NULL DEFAULT ''")
            cursor.execute("CREATE INDEX gate_gateentry_out_reason_code_idx ON gate_gateentry (out_reason_code)")
        elif connection.vendor == 'sqlite':
            cursor.execute("PRAGMA table_info(gate_gateentry)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'out_reason_code' in columns:
                return
            cursor.execute("ALTER TABLE gate_gateentry ADD COLUMN out_reason_code VARCHAR(32) NOT NULL DEFAULT ''")
            cursor.execute("CREATE INDEX gate_gateentry_out_reason_code_idx ON gate_gateentry (out_reason_code)")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0036_gate_policy_and_out_reason_code'),
    ]

    operations = [
        migrations.RunPython(add_out_reason_code_if_missing, noop),
    ]
