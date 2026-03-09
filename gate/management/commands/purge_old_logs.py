"""
Purge or archive gate entries and attendance logs older than a given number of months.
Supports retention policy (e.g. keep logs 1–2 years).
Usage: python manage.py purge_old_logs --older-than-months 24 [--dry-run] [--gate-only | --logs-only]
"""

import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from gate.models import GateEntry, AttendanceLog


class Command(BaseCommand):
    help = 'Purge gate entries and attendance logs older than N months (retention policy)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--older-than-months',
            type=int,
            default=24,
            help='Delete records older than this many months (default: 24).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report what would be deleted; do not delete.',
        )
        parser.add_argument(
            '--gate-only',
            action='store_true',
            help='Only purge GateEntry records.',
        )
        parser.add_argument(
            '--logs-only',
            action='store_true',
            help='Only purge AttendanceLog records.',
        )

    def handle(self, *args, **options):
        months = options['older_than_months']
        if months < 1:
            self.stderr.write(self.style.ERROR('--older-than-months must be >= 1.'))
            return
        cutoff = timezone.now() - datetime.timedelta(days=months * 31)
        dry_run = options['dry_run']
        gate_only = options['gate_only']
        logs_only = options['logs_only']
        if not gate_only and not logs_only:
            gate_only = logs_only = False  # do both
        else:
            if gate_only:
                logs_only = False
            else:
                gate_only = False

        self.stdout.write(f'Cutoff date: {cutoff.date()} (older than {months} months)')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made.'))

        with transaction.atomic():
            if not logs_only:
                gate_qs = GateEntry.objects.filter(timestamp__lt=cutoff)
                gate_count = gate_qs.count()
                self.stdout.write(f'GateEntry: {gate_count} record(s) would be deleted.')
                if not dry_run and gate_count:
                    gate_qs.delete()
                    self.stdout.write(self.style.SUCCESS(f'Deleted {gate_count} GateEntry record(s).'))
            if not gate_only:
                logs_qs = AttendanceLog.objects.filter(scan_time__lt=cutoff)
                logs_count = logs_qs.count()
                self.stdout.write(f'AttendanceLog: {logs_count} record(s) would be deleted.')
                if not dry_run and logs_count:
                    logs_qs.delete()
                    self.stdout.write(self.style.SUCCESS(f'Deleted {logs_count} AttendanceLog record(s).'))

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run complete. Run without --dry-run to apply.'))
