"""
Delete all application log / audit / gate history data (destructive).

Clears:
  AuditLog, GateActivityLog, GateNotification, GateHandoverNoteRead, GateHandoverNote,
  GateShift, AdminNotification, NotificationRead,
  GateEntry, GateIncident, AttendanceLog

Optional (--include-visitors): VisitorVisit, VisitorEntry
Optional (--include-event-attendance): EventAttendance rows

Does NOT delete: students, users, events, courses, or visitor pass definitions.

Usage:
  python manage.py clear_all_logs --yes
  python manage.py clear_all_logs --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Delete all audit, gate, attendance, and notification log records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Required to actually delete (safety).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show counts only; no deletes.',
        )
        parser.add_argument(
            '--include-visitors',
            action='store_true',
            help='Also delete VisitorVisit and VisitorEntry records.',
        )
        parser.add_argument(
            '--include-event-attendance',
            action='store_true',
            help='Also delete EventAttendance rows (event check-in/out history).',
        )

    def handle(self, *args, **options):
        from gate.models import (
            AuditLog,
            GateActivityLog,
            GateNotification,
            GateHandoverNoteRead,
            GateHandoverNote,
            GateShift,
            AdminNotification,
            NotificationRead,
            GateEntry,
            GateIncident,
            AttendanceLog,
            VisitorVisit,
            VisitorEntry,
            EventAttendance,
        )

        models_core = [
            ('GateActivityLog', GateActivityLog),
            ('GateHandoverNoteRead', GateHandoverNoteRead),
            ('GateHandoverNote', GateHandoverNote),
            ('GateNotification', GateNotification),
            ('GateShift', GateShift),
            ('AdminNotification', AdminNotification),
            ('GateEntry', GateEntry),
            ('GateIncident', GateIncident),
            ('AttendanceLog', AttendanceLog),
            ('AuditLog', AuditLog),
            ('NotificationRead', NotificationRead),
        ]
        models_extra = []
        if options['include_visitors']:
            models_extra.extend([
                ('VisitorVisit', VisitorVisit),
                ('VisitorEntry', VisitorEntry),
            ])
        if options['include_event_attendance']:
            models_extra.append(('EventAttendance', EventAttendance))

        all_models = models_core + models_extra

        self.stdout.write(self.style.WARNING('Tables to clear:'))
        total = 0
        for name, model in all_models:
            n = model.objects.count()
            total += n
            self.stdout.write(f'  {name}: {n} row(s)')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f'DRY RUN — would delete {total} row(s) total. Omit --dry-run and pass --yes to execute.'))
            return

        if not options['yes']:
            self.stderr.write(self.style.ERROR('Refusing to delete. Pass --yes to confirm, or --dry-run to preview counts.'))
            return

        with transaction.atomic():
            for name, model in all_models:
                n, _ = model.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'Deleted {name} ({n} object(s)).'))

        self.stdout.write(self.style.SUCCESS(f'Done. Cleared {total} row(s) across log tables.'))
