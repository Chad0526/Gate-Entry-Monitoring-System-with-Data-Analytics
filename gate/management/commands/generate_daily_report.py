"""
Generate daily report: entry summary by dept/year, peak times, denied scans.
Recommended: run at 11:59 PM (cron/Task Scheduler).
Usage: python manage.py generate_daily_report [--date YYYY-MM-DD]
"""

import json
import csv
import datetime
from io import StringIO
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count

from gate.models import GateEntry, AttendanceLog, Student, GeneratedReport


class Command(BaseCommand):
    help = 'Generate daily report (entry summary by dept/year, peak times, denied scans)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Report date (YYYY-MM-DD). Default: yesterday.',
        )
        parser.add_argument(
            '--no-file',
            action='store_true',
            help='Do not attach a CSV file to the report.',
        )

    def handle(self, *args, **options):
        if options['date']:
            try:
                report_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR('Invalid --date. Use YYYY-MM-DD.'))
                return
        else:
            report_date = timezone.localdate() - datetime.timedelta(days=1)

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(
            datetime.datetime.combine(report_date, datetime.time.min), tz
        )
        end = timezone.make_aware(
            datetime.datetime.combine(report_date, datetime.time.max), tz
        )

        entries = GateEntry.objects.filter(timestamp__gte=start, timestamp__lte=end)
        granted = entries.filter(granted=True).count()
        denied = entries.filter(granted=False).count()
        logs = AttendanceLog.objects.filter(
            scan_time__gte=start, scan_time__lte=end, voided=False
        )
        success_scans = logs.filter(result='SUCCESS').count()

        # By course/year_level (from gate entries)
        section_counts = {}
        for e in entries.select_related('student'):
            if e.student_id and e.granted:
                s = e.student
                course = getattr(s, 'course_or_section', None) or '—'
                year = getattr(s, 'year_level', None) or '—'
                key = (course, year)
                section_counts[key] = section_counts.get(key, 0) + 1
        by_dept_year = [
            {'course_section': str(k[0]), 'year_level': str(k[1]), 'count': v}
            for k, v in sorted(section_counts.items())
        ]

        # Peak hours (event scans by hour) - using Python to avoid MySQL timezone issues
        from collections import defaultdict
        hour_counts_dict = defaultdict(int)
        for log in logs:
            if log.scan_time:
                local_dt = timezone.localtime(log.scan_time)
                hour_counts_dict[local_dt.hour] += 1
        # Sort by count descending, take top 5
        peak_hours = [
            {'hour': h, 'count': c}
            for h, c in sorted(hour_counts_dict.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Denied scans (gate)
        denied_list = list(
            entries.filter(granted=False).values_list('student__student_id', 'timestamp', 'notes')[:100]
        )
        denied_list = [
            {'student_id': s or '—', 'time': str(t), 'notes': (n or '')[:80]}
            for s, t, n in denied_list
        ]

        summary = {
            'granted': granted,
            'denied': denied,
            'event_scan_success': success_scans,
            'by_dept_year': by_dept_year,
            'peak_hours': peak_hours,
            'denied_sample': denied_list,
        }
        title = f'Daily report – {report_date.isoformat()}'

        report = GeneratedReport.objects.create(
            report_type='daily',
            period_start=report_date,
            period_end=report_date,
            title=title,
            summary=json.dumps(summary, default=str),
            generated_by=None,
        )

        if not options['no_file']:
            try:
                buf = StringIO()
                w = csv.writer(buf)
                w.writerow(['Daily report', report_date.isoformat()])
                w.writerow(['Gate granted', granted])
                w.writerow(['Gate denied', denied])
                w.writerow(['Event scan success', success_scans])
                w.writerow([])
                w.writerow(['By course/section', 'Year level', 'Entries'])
                for row in by_dept_year:
                    w.writerow([row['course_section'], row['year_level'], row['count']])
                w.writerow([])
                w.writerow(['Peak hour', 'Scans'])
                for row in peak_hours:
                    w.writerow([f"{row['hour']}:00", row['count']])
                w.writerow([])
                w.writerow(['Denied (sample)', 'Time', 'Notes'])
                for row in denied_list:
                    w.writerow([row['student_id'], row['time'], row['notes']])
                from django.core.files.base import ContentFile
                report.file.save(
                    f'daily_report_{report_date.isoformat()}.csv',
                    ContentFile(buf.getvalue().encode('utf-8')),
                    save=True,
                )
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'Could not save file: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created daily report: {report.id} – {title}'))
