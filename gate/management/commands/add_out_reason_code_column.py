"""
One-time fix: add out_reason_code to gate_gateentry on MySQL if missing.
Run with the same .env as your server (DB_ENGINE=mysql): python manage.py add_out_reason_code_column
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Add out_reason_code column to gate_gateentry if missing (MySQL)."

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            self.stdout.write(self.style.WARNING(
                "Database is %s, not MySQL. Column is added by migration 0036/0037. Run: python manage.py migrate gate"
            ) % connection.vendor)
            return

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'gate_gateentry' AND COLUMN_NAME = 'out_reason_code'
            """)
            if cursor.fetchone()[0] > 0:
                self.stdout.write(self.style.SUCCESS("Column gate_gateentry.out_reason_code already exists."))
                return

            self.stdout.write("Adding column gate_gateentry.out_reason_code ...")
            cursor.execute("""
                ALTER TABLE gate_gateentry
                ADD COLUMN out_reason_code VARCHAR(32) NOT NULL DEFAULT ''
            """)
            try:
                cursor.execute("CREATE INDEX gate_gateentry_out_reason_code_idx ON gate_gateentry (out_reason_code)")
            except Exception as e:
                if "Duplicate key name" in str(e) or "1061" in str(e):
                    pass
                else:
                    raise
            self.stdout.write(self.style.SUCCESS("Column out_reason_code added. Reload /gate/entries/."))
