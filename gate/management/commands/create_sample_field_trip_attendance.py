"""Create a sample field trip event and sample attendance records.
Usage: python manage.py create_sample_field_trip_attendance
"""
import datetime
import io
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max
from django.core.files.base import ContentFile

from gate.models import (
    Event,
    EventCategory,
    EventImage,
    JobCategory,
    EventAttendance,
    Student,
)

User = get_user_model()


def make_placeholder_image():
    """Return a minimal PNG as bytes for EventImage (so event list/detail don't break)."""
    try:
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new('RGB', (400, 200), color=(70, 130, 180))
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Create a sample field trip event and sample EventAttendance records for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=8,
            help='Number of sample attendance records to create (default 8)',
        )

    def handle(self, *args, **options):
        user = User.objects.first()
        if not user:
            self.stderr.write(self.style.ERROR('No user in the database. Create a user first (e.g. superuser).'))
            return

        count = max(1, min(options['count'], 50))
        today = timezone.localdate()
        start = today
        end = today + datetime.timedelta(days=1)

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

        name = 'CCB Sample Field Trip - Museum Visit (Demo)'
        event = Event.objects.filter(name=name).first()
        created_event = False

        if not event:
            try:
                with transaction.atomic():
                    event = Event.objects.create(
                        category=category,
                        job_category=job_cat,
                        name=name,
                        description=(
                            '<p>Sample <strong>field trip</strong> event for testing.</p>'
                            '<p>Use "Take attendance" (field trip scan) to record attendance; '
                            'no gate entry is created.</p>'
                        ),
                        venue='City Museum / Off-campus',
                        start_date=start,
                        end_date=end,
                        points=15,
                        status='active',
                        attendance_mode='OPEN',
                        event_location='field_trip',
                        created_user=user,
                        updated_user=user,
                    )
                    created_event = True
                    # Attach a placeholder image so event list/detail pages work
                    png_bytes = make_placeholder_image()
                    if png_bytes:
                        fname = f'sample_field_trip_{event.pk}.png'
                        event_image = EventImage.objects.create(event=event)
                        event_image.image.save(fname, ContentFile(png_bytes), save=True)
                    else:
                        self.stdout.write(self.style.WARNING('No placeholder image (PIL); add an image in Admin for event detail.'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to create event: {e}'))
                raise
            self.stdout.write(self.style.SUCCESS(f'Created field trip event: "{event.name}" (id={event.pk}).'))
        else:
            self.stdout.write(f'Using existing field trip event: "{event.name}" (id={event.pk}).')

        if getattr(event, 'event_location', 'on_campus') != 'field_trip':
            self.stdout.write(self.style.WARNING(
                f'Event "{event.name}" is not a field trip (event_location={getattr(event, "event_location", "?")}). '
                'Set event_location to "Field trip / Off-campus" in Admin.'
            ))

        students = list(Student.objects.filter(is_active=True).order_by('pk')[:count * 2])
        if not students:
            self.stdout.write(self.style.WARNING('No active students in the database. Add students to create attendance records.'))
            if created_event:
                self.stdout.write('  Field trip event created. Take attendance via: Event detail > Take attendance')
            return

        now = timezone.now()
        added = 0
        for i, student in enumerate(students):
            if added >= count:
                break
            att, created = EventAttendance.objects.get_or_create(
                student=student,
                event=event,
                defaults={
                    'participated': True,
                    'checked_in_at': now - datetime.timedelta(minutes=30 + i * 5),
                    'checked_out_at': None,
                },
            )
            if created:
                added += 1
                # Some get checked out
                if added % 3 == 0:
                    att.checked_out_at = now - datetime.timedelta(minutes=5 + added)
                    att.save(update_fields=['checked_out_at'])

        self.stdout.write(self.style.SUCCESS(f'Created {added} sample attendance record(s) for "{event.name}".'))
        self.stdout.write('  Event detail (Take attendance): /gate/detail/{}/'.format(event.pk))
        self.stdout.write('  Gate scanner (event): /gate/?event={}'.format(event.pk))
        self.stdout.write('  Admin EventAttendance: /admin/gate/eventattendance/')
