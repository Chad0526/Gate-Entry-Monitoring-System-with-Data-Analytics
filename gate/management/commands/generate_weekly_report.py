"""
Generate weekly report: week-over-week trends, top peak hours, students with repeated anomalies.
Recommended: run Monday 7:00 AM (cron/Task Scheduler).
Usage: python manage.py generate_weekly_report [--week-ending YYYY-MM-DD]
"""

import json
import datetime
from io import StringIO
import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count

from gate.models import GateEntry, AttendanceLog, Student, GeneratedReport


def week_range(date):
    """Return (monday, sunday) for the week containing date."""
    # Monday = 0
    idx = (date.weekday()) % 7
    monday = date - datetime.timedelta(days=idx)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


class Command(BaseCommand):
    help = 'Generate weekly report (trends, peak hours, repeated anomalies)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--week-ending',
            type=str,
            default=None,
            help='Sunday of the week (YYYY-MM-DD). Default: last Sunday.',
        )
        parser.add_argument(
            '--no-file',
            action='store_true',
            help='Do not attach a CSV file.',
        )

    def handle(self, *args, **options):
        if options['week_ending']:
            try:
                sunday = datetime.datetime.strptime(options['week_ending'], '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR('Invalid --week-ending. Use YYYY-MM-DD.'))
                return
        else:
            # Last completed week (ending last Sunday)
            today = timezone.localdate()
            days_back = (today.weekday() + 1) % 7
            if days_back == 0:
                days_back = 7
            sunday = today - datetime.timedelta(days=days_back)
        monday, end_sunday = week_range(sunday)

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(
            datetime.datetime.combine(monday, datetime.time.min), tz
        )
        end = timezone.make_aware(
            datetime.datetime.combine(end_sunday, datetime.time.max), tz
        )

        entries = GateEntry.objects.filter(timestamp__gte=start, timestamp__lte=end)
        granted = entries.filter(granted=True).count()
        denied = entries.filter(granted=False).count()
        logs = AttendanceLog.objects.filter(
            scan_time__gte=start, scan_time__lte=end, voided=False
        )
        success_scans = logs.filter(result='SUCCESS').count()

        # Top peak hours - using Python to avoid MySQL timezone issues
        from collections import defaultdict
        hour_counts_dict = defaultdict(int)
        for log in logs:
            if log.scan_time:
                local_dt = timezone.localtime(log.scan_time)
                hour_counts_dict[local_dt.hour] += 1
        # Sort by count descending, take top 10
        peak_hours = [
            {'hour': h, 'count': c}
            for h, c in sorted(hour_counts_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Students with repeated anomalies (multiple denied gate entries)
        denied_by_student = (
            entries.filter(granted=False)
            .values('student_id')
            .annotate(denied_count=Count('id'))
            .filter(denied_count__gte=2)
            .order_by('-denied_count')[:50]
        )
        student_ids = [r['student_id'] for r in denied_by_student if r['student_id']]
        students_map = {s.id: s for s in Student.objects.filter(id__in=student_ids)}
        repeated_anomalies = []
        for r in denied_by_student:
            s = students_map.get(r['student_id'])
            repeated_anomalies.append({
                'student_id': s.student_id if s else str(r['student_id']),
                'name': s.get_full_name() if s else '—',
                'denied_count': r['denied_count'],
            })

        # Simple week-over-week: compare to previous week
        prev_monday = monday - datetime.timedelta(days=7)
        prev_sunday = end_sunday - datetime.timedelta(days=7)
        prev_start = timezone.make_aware(
            datetime.datetime.combine(prev_monday, datetime.time.min), tz
        )
        prev_end = timezone.make_aware(
            datetime.datetime.combine(prev_sunday, datetime.time.max), tz
        )
        prev_granted = GateEntry.objects.filter(
            timestamp__gte=prev_start, timestamp__lte=prev_end, granted=True
        ).count()
        prev_denied = GateEntry.objects.filter(
            timestamp__gte=prev_start, timestamp__lte=prev_end, granted=False
        ).count()
        trend = {
            'this_week_granted': granted,
            'this_week_denied': denied,
            'prev_week_granted': prev_granted,
            'prev_week_denied': prev_denied,
        }

        summary = {
            'granted': granted,
            'denied': denied,
            'event_scan_success': success_scans,
            'peak_hours': peak_hours,
            'repeated_anomalies': repeated_anomalies,
            'trend_vs_prev_week': trend,
        }
        title = f'Weekly report – {monday.isoformat()} to {end_sunday.isoformat()}'

        report = GeneratedReport.objects.create(
            report_type='weekly',
            period_start=monday,
            period_end=end_sunday,
            title=title,
            summary=json.dumps(summary, default=str),
            generated_by=None,
        )

        if not options['no_file']:
            try:
                buf = StringIO()
                w = csv.writer(buf)
                w.writerow(['Weekly report', f'{monday} to {end_sunday}'])
                w.writerow(['Gate granted', granted])
                w.writerow(['Gate denied', denied])
                w.writerow(['Event scan success', success_scans])
                w.writerow([])
                w.writerow(['Peak hour', 'Scans'])
                for row in peak_hours:
                    w.writerow([f"{row['hour']}:00", row['count']])
                w.writerow([])
                w.writerow(['Student ID', 'Name', 'Denied count (repeated anomalies)'])
                for row in repeated_anomalies:
                    w.writerow([row['student_id'], row['name'], row['denied_count']])
                from django.core.files.base import ContentFile
                report.file.save(
                    f'weekly_report_{monday.isoformat()}.csv',
                    ContentFile(buf.getvalue().encode('utf-8')),
                    save=True,
                )
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'Could not save file: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created weekly report: {report.id} – {title}'))
