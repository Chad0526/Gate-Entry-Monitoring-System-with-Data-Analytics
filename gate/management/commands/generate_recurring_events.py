"""Generate events from recurring templates (weekly/monthly). Creates one event per template for the next occurrence.
Requires: RecurringEventTemplate (name, venue); at least one Event with same category (so location can be copied).
Uses first active EventCategory and first JobCategory.
Usage: python manage.py generate_recurring_events [--dry-run]
"""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from gate.models import RecurringEventTemplate, Event, EventCategory, JobCategory


class Command(BaseCommand):
    help = 'Generate events from recurring templates'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only print what would be created')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        category = EventCategory.objects.filter(status='active').first()
        job_cat = JobCategory.objects.first()
        if not category or not job_cat:
            self.stderr.write(self.style.WARNING('Need at least one EventCategory and JobCategory.'))
            return
        today = timezone.localdate()
        created = 0
        for t in RecurringEventTemplate.objects.filter(is_active=True):
            next_date = None
            if t.recurrence == 'weekly' and t.day_of_week is not None:
                # next occurrence of this weekday
                days_ahead = (t.day_of_week - today.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                next_date = today + datetime.timedelta(days=days_ahead)
            elif t.recurrence == 'monthly' and t.day_of_month is not None:
                d = t.day_of_month
                if today.day < d:
                    try:
                        next_date = today.replace(day=min(d, 28))
                    except ValueError:
                        next_date = today.replace(day=28)
                else:
                    try:
                        next_date = (today.replace(day=1) + datetime.timedelta(days=32)).replace(
                            day=min(d, 28))
                    except ValueError:
                        next_date = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=28)
            if not next_date:
                continue
            name = f"{t.name} – {next_date.isoformat()}"
            if Event.objects.filter(name=name).exists():
                continue
            if dry_run:
                self.stdout.write(f'Would create: {name}')
                created += 1
                continue
            try:
                with transaction.atomic():
                    # LocationField may require a dict with mapbox format; copy from existing event if needed
                    Event.objects.create(
                        category=category,
                        job_category=job_cat,
                        name=name,
                        description='<p>Recurring event.</p>',
                        venue=t.venue or 'TBA',
                        start_date=next_date,
                        end_date=next_date,
                        points=0,
                        maximum_attende=100,
                        status='scheduled',
                    )
                    t.last_generated = next_date
                    t.save(update_fields=['last_generated'])
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f'Created: {name}'))
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'Skip {t.name}: {e}'))
        self.stdout.write(self.style.SUCCESS(f'Done. Created {created} event(s).'))
