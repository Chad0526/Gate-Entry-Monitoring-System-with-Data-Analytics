"""Create a sample event so you can see it in Admin and on the guard dashboard.
Usage: python manage.py create_sample_event
"""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max

from gate.models import Event, EventCategory, JobCategory

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a sample event (scheduled) for testing in Admin and guard dashboard'

    def handle(self, *args, **options):
        # Need at least one user for category creation if we create one
        user = User.objects.first()
        if not user:
            self.stderr.write(self.style.ERROR('No user in the database. Create a user first (e.g. superuser).'))
            return

        today = timezone.localdate()
        start = today
        end = today + datetime.timedelta(days=1)

        # Use existing category and job category, or create minimal ones
        category = EventCategory.objects.filter(status='active').first()
        if not category:
            category = EventCategory.objects.first()
        if not category:
            self.stdout.write('Creating sample EventCategory...')
            priority = (EventCategory.objects.aggregate(m=Max('priority'))['m'] or 0) + 1
            category = EventCategory.objects.create(
                name='Sample / General',
                code='SAMP',
                priority=priority,
                status='active',
                created_user=user,
                updated_user=user,
            )

        job_cat = JobCategory.objects.first()
        if not job_cat:
            self.stdout.write('Creating sample JobCategory...')
            job_cat = JobCategory.objects.create(name='General')

        name = 'CCB Sample Event - Campus Orientation (Demo)'
        if Event.objects.filter(name=name).exists():
            self.stdout.write(self.style.WARNING(f'Event "{name}" already exists. Nothing to do.'))
            return

        # LocationField stores (lat, lon) as "lat,lon". Use a generic point (e.g. Bayawan area).
        try:
            with transaction.atomic():
                event = Event.objects.create(
                    category=category,
                    job_category=job_cat,
                    name=name,
                    description=(
                        '<p>This is a <strong>sample event</strong> created for testing.</p>'
                        '<p>You can see it in Django Admin (Events) and on the guard dashboard '
                        '(Campus analytics / Event program schedule).</p>'
                        '<p>Edit or delete it from Admin when done.</p>'
                    ),
                    venue='Main Hall / CCB Campus',
                    start_date=start,
                    end_date=end,
                    points=10,
                    maximum_attende=100,
                    status='scheduled',
                    attendance_mode='OPEN',
                    created_user=user,
                    updated_user=user,
                )
            self.stdout.write(self.style.SUCCESS(
                'Created sample event: "%s" (status=%s, %s to %s).'
                % (event.name, event.status, event.start_date, event.end_date)
            ))
            self.stdout.write('  View in Admin: /admin/gate/event/')
            self.stdout.write('  View on dashboard: Gate & Attendance > Campus analytics / Event list')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to create event: {e}'))
            raise
