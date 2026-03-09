"""
Test database connection (MySQL/XAMPP). Run from project root: python manage.py check_db
"""
import socket
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Test database connection (useful when MySQL connection fails)."

    def handle(self, *args, **options):
        db = settings.DATABASES.get('default', {})
        engine = db.get('ENGINE', '')
        host = db.get('HOST', '')
        port = db.get('PORT', 3306)

        self.stdout.write("Database engine: %s" % engine)
        self.stdout.write("Host: %s  Port: %s" % (host, port))

        if 'mysql' not in engine:
            self.stdout.write(self.style.SUCCESS("Not using MySQL. Connection check skipped."))
            return

        # 1. Raw TCP check
        self.stdout.write("")
        for try_host in (host, '127.0.0.1', 'localhost'):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((try_host, int(port)))
                s.close()
                self.stdout.write(self.style.SUCCESS("  Port %s:%s is open (TCP)." % (try_host, port)))
                break
            except Exception as e:
                self.stdout.write(self.style.WARNING("  %s:%s - %s" % (try_host, port, e)))
        else:
            self.stdout.write(self.style.ERROR(
                "MySQL is not accepting connections on port %s.\n"
                "  - Open XAMPP Control Panel and click Start next to MySQL.\n"
                "  - If MySQL won't start, check if another program uses port 3306 (e.g. another MySQL)."
            ))
            return

        # 2. Django DB connection
        self.stdout.write("")
        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS("Django connected to MySQL successfully."))
        except OperationalError as e:
            self.stdout.write(self.style.ERROR("Django could not connect: %s" % e))
            self.stdout.write(
                "  - Ensure the database '%s' exists (create it in phpMyAdmin if needed).\n"
                "  - Check .env: DB_HOST=%s, DB_PORT=%s, DB_USER=%s, DB_NAME=%s."
                % (db.get('NAME'), host, port, db.get('USER'), db.get('NAME'))
            )
