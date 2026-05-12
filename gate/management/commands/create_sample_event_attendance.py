"""Create sample EventAttendance records for a SPECIFIC, already-existing event.

Use this when you already have an event (created in Admin or via
`create_sample_event`) and want quick demo attendance for it.

Examples:
    # 1) See available events with their IDs so you can pick one
    python manage.py create_sample_event_attendance --list

    # 2) Add 10 sample attendees to event id=5
    python manage.py create_sample_event_attendance --event-id 5 --count 10

    # 3) Match an event by (case-insensitive) name fragment
    python manage.py create_sample_event_attendance --event-name "Orientation" --count 8

    # 4) Use ALL active students (ignores --count)
    python manage.py create_sample_event_attendance --event-id 5 --all

    # 5) Control how many of the created records also have a check-out time
    python manage.py create_sample_event_attendance --event-id 5 --count 20 --checkout-ratio 0.5

    # 6) Wipe existing attendance for that event before re-creating
    python manage.py create_sample_event_attendance --event-id 5 --count 10 --reset
"""
import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from gate.models import Event, EventAttendance, Student


class Command(BaseCommand):
    help = 'Create sample EventAttendance records for an existing event (pick by id or name).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='Just list available events (id, name, status, dates) and exit.',
        )
        parser.add_argument(
            '--event-id',
            type=int,
            default=None,
            help='Primary key of the event to attach attendance to.',
        )
        parser.add_argument(
            '--event-name',
            type=str,
            default=None,
            help='Case-insensitive fragment of the event name. Must match exactly one event.',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of sample attendance records to create (default 10, max 200). Ignored with --all.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create attendance for ALL active students (ignores --count).',
        )
        parser.add_argument(
            '--checkout-ratio',
            type=float,
            default=0.33,
            help='Fraction (0.0-1.0) of created records that will also have a check-out time. Default 0.33.',
        )
        parser.add_argument(
            '--participated',
            action='store_true',
            default=True,
            help='Mark created records as participated=True (default).',
        )
        parser.add_argument(
            '--non-participant',
            action='store_true',
            help='Mark created records as participated=False instead.',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing EventAttendance for this event before creating new ones.',
        )

    def handle(self, *args, **options):
        if options['list']:
            self._list_events()
            return

        event = self._resolve_event(options)

        if options['reset']:
            deleted, _ = EventAttendance.objects.filter(event=event).delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing attendance row(s) for "{event.name}".'))

        participated = not options['non_participant']
        checkout_ratio = max(0.0, min(1.0, options['checkout_ratio']))

        students_qs = Student.objects.filter(is_active=True).order_by('pk')
        if options['all']:
            students = list(students_qs)
        else:
            count = max(1, min(options['count'], 200))
            # Take a bit more than count so we can skip over any that already
            # have an attendance record for this event.
            students = list(students_qs[: count * 3])

        if not students:
            self.stderr.write(self.style.ERROR(
                'No active students found. Register/approve some students first.'
            ))
            return

        target = len(students) if options['all'] else max(1, min(options['count'], 200))

        now = timezone.now()
        created_count = 0
        skipped = 0

        try:
            with transaction.atomic():
                for i, student in enumerate(students):
                    if not options['all'] and created_count >= target:
                        break

                    check_in = now - datetime.timedelta(minutes=30 + (i * 3) + random.randint(0, 15))
                    att, created = EventAttendance.objects.get_or_create(
                        student=student,
                        event=event,
                        defaults={
                            'participated': participated,
                            'checked_in_at': check_in,
                        },
                    )

                    if not created:
                        skipped += 1
                        continue

                    created_count += 1

                    # Optionally also set a check-out time on a portion of the records
                    if random.random() < checkout_ratio:
                        att.checked_out_at = check_in + datetime.timedelta(
                            minutes=random.randint(15, 90)
                        )
                        att.save(update_fields=['checked_out_at'])
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Failed while creating attendance: {exc}'))
            raise

        self.stdout.write(self.style.SUCCESS(
            f'Created {created_count} attendance record(s) for "{event.name}" (id={event.pk}).'
        ))
        if skipped:
            self.stdout.write(self.style.WARNING(
                f'Skipped {skipped} student(s) that already had attendance for this event '
                '(use --reset to clear first).'
            ))
        self.stdout.write('  Event detail:      /gate/detail/{}/'.format(event.pk))
        self.stdout.write('  Admin attendance:  /admin/gate/eventattendance/?event__id__exact={}'.format(event.pk))

    # ------------------------------------------------------------------ helpers

    def _list_events(self):
        events = Event.objects.all().order_by('-start_date', 'name')[:50]
        if not events:
            self.stdout.write(self.style.WARNING('No events found. Create one first (Admin or `create_sample_event`).'))
            return
        self.stdout.write(self.style.NOTICE('Most recent events (id | status | dates | name):'))
        for ev in events:
            self.stdout.write(
                '  {id:>5}  {status:<10}  {start} -> {end}  {name}'.format(
                    id=ev.pk,
                    status=getattr(ev, 'status', '') or '',
                    start=ev.start_date,
                    end=ev.end_date,
                    name=ev.name,
                )
            )
        self.stdout.write('')
        self.stdout.write('Next: python manage.py create_sample_event_attendance --event-id <ID> --count 10')

    def _resolve_event(self, options):
        event_id = options.get('event_id')
        name_fragment = options.get('event_name')

        if not event_id and not name_fragment:
            raise CommandError(
                'You must pass --event-id or --event-name (or run with --list to see available events).'
            )

        if event_id:
            try:
                return Event.objects.get(pk=event_id)
            except Event.DoesNotExist:
                raise CommandError(f'No event with id={event_id}. Try --list to see available events.')

        matches = list(Event.objects.filter(name__icontains=name_fragment))
        if not matches:
            raise CommandError(f'No event name contains "{name_fragment}". Try --list to see available events.')
        if len(matches) > 1:
            joined = '\n'.join(f'    [{e.pk}] {e.name}' for e in matches[:10])
            raise CommandError(
                f'Multiple events match "{name_fragment}":\n{joined}\n'
                'Re-run with --event-id <ID> to disambiguate.'
            )
        return matches[0]
