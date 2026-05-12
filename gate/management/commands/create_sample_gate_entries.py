"""Create sample GateEntry (IN/OUT) scans for testing the dashboard and reports.

By default it creates realistic IN + OUT pairs for N active students on
today's local date. You can pick a different date, attach the scans to a
specific event, and control denied/duplicate ratios.

`GateEntry.timestamp` is `auto_now_add`, so we create the row first then
override the timestamp with a queryset `.update()` (same trick the test
suite uses).

Examples:
    # Smoke test: 10 students, IN+OUT pairs, today
    python manage.py create_sample_gate_entries --count 10

    # Pick a specific day (local date)
    python manage.py create_sample_gate_entries --count 20 --date 2026-05-11

    # IN scans only (no OUT)
    python manage.py create_sample_gate_entries --count 15 --in-only

    # Attach all scans to a specific event (e.g. event id=7)
    python manage.py create_sample_gate_entries --count 15 --event-id 7

    # Use EVERY active student (ignores --count)
    python manage.py create_sample_gate_entries --all

    # Sprinkle in 20% denied scans for the analytics charts
    python manage.py create_sample_gate_entries --count 25 --denied-ratio 0.2

    # Wipe today's entries first, then recreate
    python manage.py create_sample_gate_entries --count 10 --reset
"""
import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from gate.models import Event, GateEntry, Student

User = get_user_model()

# Realistic windows (24h, local time)
MORNING_IN_HOURS = (7, 9)      # 07:00 - 09:59
EVENING_OUT_HOURS = (15, 17)   # 15:00 - 17:59

OUT_REASON_CODES = ['NO_CLASS_WINDOW', 'LUNCH', 'ALL_CLASSES_DONE', 'OFFICIAL_BUSINESS']


def _local_day_bounds(date):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.datetime.combine(date, datetime.time.min), tz)
    end = start + datetime.timedelta(days=1)
    return start, end


def _random_dt_for(date, hour_start, hour_end):
    """Return an aware datetime on `date` at a random time within [hour_start, hour_end]."""
    tz = timezone.get_current_timezone()
    hour = random.randint(hour_start, hour_end)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    naive = datetime.datetime.combine(date, datetime.time(hour, minute, second))
    return timezone.make_aware(naive, tz)


class Command(BaseCommand):
    help = 'Create sample GateEntry IN/OUT scans for testing the dashboard and reports.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of students to generate entries for (default 10, max 500). Ignored with --all.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Use ALL active students (ignores --count).',
        )
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Date for the scans (YYYY-MM-DD). Defaults to today (local).',
        )
        parser.add_argument(
            '--in-only',
            action='store_true',
            help='Only create IN scans (skip OUT).',
        )
        parser.add_argument(
            '--out-ratio',
            type=float,
            default=0.85,
            help='Fraction (0.0-1.0) of IN scans that also get an OUT scan. Default 0.85.',
        )
        parser.add_argument(
            '--denied-ratio',
            type=float,
            default=0.0,
            help='Fraction (0.0-1.0) of IN scans that are DENIED instead of SUCCESS. Default 0.0.',
        )
        parser.add_argument(
            '--event-id',
            type=int,
            default=None,
            help='Attach scans to this Event id (optional).',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing gate entries for the target date before creating new ones.',
        )
        parser.add_argument(
            '--list-students',
            action='store_true',
            help='Just list a few active students (id and name) and exit.',
        )

    def handle(self, *args, **options):
        if options['list_students']:
            self._list_students()
            return

        target_date = self._parse_date(options['date'])
        out_ratio = max(0.0, min(1.0, options['out_ratio']))
        denied_ratio = max(0.0, min(1.0, options['denied_ratio']))
        in_only = options['in_only']

        event = None
        if options['event_id']:
            try:
                event = Event.objects.get(pk=options['event_id'])
            except Event.DoesNotExist:
                raise CommandError(
                    f'No event with id={options["event_id"]}. '
                    'Run `python manage.py create_sample_event_attendance --list` to see event IDs.'
                )

        # Optional reset
        if options['reset']:
            day_start, day_end = _local_day_bounds(target_date)
            qs = GateEntry.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            deleted = qs.count()
            qs.delete()
            self.stdout.write(self.style.WARNING(
                f'Deleted {deleted} existing gate entr{"y" if deleted == 1 else "ies"} for {target_date}.'
            ))

        # Pick students
        students_qs = Student.objects.filter(is_active=True).order_by('pk')
        if options['all']:
            students = list(students_qs)
        else:
            count = max(1, min(options['count'], 500))
            students = list(students_qs[:count])

        if not students:
            self.stderr.write(self.style.ERROR(
                'No active students found. Register/approve some students first.'
            ))
            return

        recorder = User.objects.filter(is_staff=True).first() or User.objects.first()

        in_created = 0
        out_created = 0
        denied_created = 0

        for student in students:
            is_denied = random.random() < denied_ratio

            in_dt = _random_dt_for(target_date, *MORNING_IN_HOURS)
            in_entry = GateEntry.objects.create(
                student=student,
                event=event,
                granted=not is_denied,
                scan_type='IN',
                result='DENIED' if is_denied else 'SUCCESS',
                notes='' if not is_denied else 'Sample denied scan (auto-generated)',
                recorded_by=recorder,
                device_id='SAMPLE-SEED',
            )
            # auto_now_add forces timestamp=now(); override it for the target date
            GateEntry.objects.filter(pk=in_entry.pk).update(timestamp=in_dt)
            in_created += 1
            if is_denied:
                denied_created += 1
                # Denied scans don't get a matching OUT
                continue

            if in_only:
                continue
            if random.random() > out_ratio:
                continue

            # OUT scan, sometime after the IN scan (still on target_date)
            out_dt = _random_dt_for(target_date, *EVENING_OUT_HOURS)
            if out_dt <= in_dt:
                out_dt = in_dt + datetime.timedelta(hours=random.randint(2, 6))

            out_entry = GateEntry.objects.create(
                student=student,
                event=event,
                granted=True,
                scan_type='OUT',
                result='SUCCESS',
                out_reason_code=random.choice(OUT_REASON_CODES),
                recorded_by=recorder,
                device_id='SAMPLE-SEED',
            )
            GateEntry.objects.filter(pk=out_entry.pk).update(timestamp=out_dt)
            out_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created gate entries on {target_date}: {in_created} IN '
            f'(of which {denied_created} DENIED) + {out_created} OUT.'
        ))
        if event:
            self.stdout.write(f'  Linked to event: [{event.pk}] {event.name}')
        self.stdout.write('  Admin gate entries: /admin/gate/gateentry/')
        self.stdout.write('  Dashboard:          /dashboard/')

    # ------------------------------------------------------------------ helpers

    def _parse_date(self, raw):
        if not raw:
            return timezone.localdate()
        try:
            return datetime.datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Invalid --date "{raw}". Use YYYY-MM-DD (e.g. 2026-05-11).')

    def _list_students(self):
        students = Student.objects.filter(is_active=True).order_by('pk')[:30]
        if not students:
            self.stdout.write(self.style.WARNING('No active students found.'))
            return
        self.stdout.write(self.style.NOTICE('First 30 active students (pk | student_id | name):'))
        for s in students:
            full_name = f'{getattr(s, "first_name", "")} {getattr(s, "last_name", "")}'.strip()
            self.stdout.write(f'  {s.pk:>5}  {s.student_id:<15}  {full_name}')
