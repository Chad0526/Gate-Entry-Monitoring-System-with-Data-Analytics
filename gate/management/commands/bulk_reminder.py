"""Send reminder email to all registered students for an event. Run before event day.
Usage: python manage.py bulk_reminder --event-id 1 [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from gate.models import Event, EventRegistration


class Command(BaseCommand):
    help = 'Send reminder email to students registered for an event'

    def add_arguments(self, parser):
        parser.add_argument('--event-id', type=int, required=True, help='Event ID')
        parser.add_argument('--dry-run', action='store_true', help='Only print recipient count')

    def handle(self, *args, **options):
        event_id = options['event_id']
        dry_run = options['dry_run']
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Event {event_id} not found.'))
            return
        regs = EventRegistration.objects.filter(event=event).select_related('student')
        emails = [r.student.email for r in regs if r.student and r.student.email]
        emails = list(set(emails))
        if not emails:
            self.stdout.write(self.style.WARNING('No email addresses for registered students.'))
            return
        if dry_run:
            self.stdout.write(f'Would send to {len(emails)} address(es) for event: {event.name}')
            return
        subject = f'Reminder: {event.name} – {event.start_date}'
        body = (
            f'You are registered for: {event.name}\n'
            f'Date: {event.start_date} to {event.end_date}\n'
            f'Venue: {event.venue}\n\n'
            'Please bring your QR code or student ID.\n'
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
        try:
            send_mail(subject, body, from_email, emails, fail_silently=True)
            self.stdout.write(self.style.SUCCESS(f'Sent reminder to {len(emails)} address(es).'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Send failed: {e}'))
