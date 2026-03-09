"""
Delete all gate entries for today (local date).
Usage: python manage.py clear_entries_today [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from gate.models import GateEntry
from gate.gate_views import _local_day_bounds


class Command(BaseCommand):
    help = 'Delete all gate entries for today (local date)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report what would be deleted; do not delete.',
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        day_start, day_end = _local_day_bounds(today)
        qs = GateEntry.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end)
        count = qs.count()

        self.stdout.write(f'Today (local): {today}')
        self.stdout.write(f'Gate entries for today: {count}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run — no changes made.'))
            return

        if count == 0:
            self.stdout.write('Nothing to delete.')
            return

        qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} gate entr{"y" if count == 1 else "ies"} for today.'))
