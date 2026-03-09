"""
Generate monthly report: executive summary, comparisons vs last month, scan success rate.
Recommended: run on the 1st of the month (cron/Task Scheduler).
Usage: python manage.py generate_monthly_report [--month YYYY-MM]
"""

import json
import datetime
from io import StringIO
import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count

from gate.models import GateEntry, AttendanceLog, Event, EventAttendance, GeneratedReport


class Command(BaseCommand):
    help = 'Generate monthly report (executive summary, vs last month, scan success rate)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            default=None,
            help='Month as YYYY-MM. Default: previous month.',
        )
        parser.add_argument(
            '--no-file',
            action='store_true',
            help='Do not attach a CSV file.',
        )

    def handle(self, *args, **options):
        if options['month']:
            try:
                year, month = map(int, options['month'].split('-'))
                last_day = datetime.date(year, month, 1)
                # last day of month
                if month == 12:
                    last_day = last_day.replace(month=12, day=31)
                else:
                    last_day = (last_day.replace(month=month + 1, day=1) -
                                datetime.timedelta(days=1))
                month_start = datetime.date(year, month, 1)
            except (ValueError, TypeError):
                self.stderr.write(self.style.ERROR('Invalid --month. Use YYYY-MM.'))
                return
        else:
            today = timezone.localdate()
            month_start = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
            year, month = month_start.year, month_start.month
            if month == 12:
                last_day = datetime.date(year, 12, 31)
            else:
                last_day = (datetime.date(year, month + 1, 1) -
                            datetime.timedelta(days=1))

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(
            datetime.datetime.combine(month_start, datetime.time.min), tz
        )
        end = timezone.make_aware(
            datetime.datetime.combine(last_day, datetime.time.max), tz
        )

        entries = GateEntry.objects.filter(timestamp__gte=start, timestamp__lte=end)
        granted = entries.filter(granted=True).count()
        denied = entries.filter(granted=False).count()
        logs = AttendanceLog.objects.filter(
            scan_time__gte=start, scan_time__lte=end, voided=False
        )
        total_scans = logs.count()
        success_scans = logs.filter(result='SUCCESS').count()
        scan_success_rate = round(100.0 * success_scans / total_scans, 1) if total_scans else 0

        # Previous month
        if month == 1:
            prev_start = datetime.date(year - 1, 12, 1)
            prev_end = datetime.date(year - 1, 12, 31)
        else:
            prev_start = datetime.date(year, month - 1, 1)
            if month - 1 == 12:
                prev_end = datetime.date(year - 1, 12, 31)
            else:
                prev_end = (datetime.date(year, month, 1) -
                            datetime.timedelta(days=1))
        prev_start_tz = timezone.make_aware(
            datetime.datetime.combine(prev_start, datetime.time.min), tz
        )
        prev_end_tz = timezone.make_aware(
            datetime.datetime.combine(prev_end, datetime.time.max), tz
        )
        prev_granted = GateEntry.objects.filter(
            timestamp__gte=prev_start_tz, timestamp__lte=prev_end_tz, granted=True
        ).count()
        prev_denied = GateEntry.objects.filter(
            timestamp__gte=prev_start_tz, timestamp__lte=prev_end_tz, granted=False
        ).count()
        prev_logs = AttendanceLog.objects.filter(
            scan_time__gte=prev_start_tz, scan_time__lte=prev_end_tz, voided=False
        )
        prev_total = prev_logs.count()
        prev_success = prev_logs.filter(result='SUCCESS').count()
        prev_rate = round(100.0 * prev_success / prev_total, 1) if prev_total else 0

        comparison = {
            'this_month_granted': granted,
            'this_month_denied': denied,
            'this_month_scan_success_rate': scan_success_rate,
            'prev_month_granted': prev_granted,
            'prev_month_denied': prev_denied,
            'prev_month_scan_success_rate': prev_rate,
        }

        # Event attendance snapshot (events in this month)
        events_in_month = Event.objects.filter(
            start_date__lte=last_day, end_date__gte=month_start
        )
        event_stats = []
        for evt in events_in_month[:20]:
            att = EventAttendance.objects.filter(
                event=evt,
                checked_in_at__gte=start,
                checked_in_at__lte=end,
            ).count()
            event_stats.append({'event_name': evt.name[:50], 'check_ins': att})
        summary = {
            'granted': granted,
            'denied': denied,
            'event_scan_success': success_scans,
            'total_scans': total_scans,
            'scan_success_rate': scan_success_rate,
            'comparison_vs_prev_month': comparison,
            'event_check_ins': event_stats,
        }
        title = f'Monthly report – {month_start.isoformat()}'

        report = GeneratedReport.objects.create(
            report_type='monthly',
            period_start=month_start,
            period_end=last_day,
            title=title,
            summary=json.dumps(summary, default=str),
            generated_by=None,
        )

        if not options['no_file']:
            try:
                buf = StringIO()
                w = csv.writer(buf)
                w.writerow(['Monthly executive summary', month_start.isoformat()])
                w.writerow(['Gate granted', granted])
                w.writerow(['Gate denied', denied])
                w.writerow(['Event scan success', success_scans])
                w.writerow(['Scan success rate (%)', scan_success_rate])
                w.writerow([])
                w.writerow(['Vs previous month', 'This month', 'Previous month'])
                w.writerow(['Granted', granted, prev_granted])
                w.writerow(['Denied', denied, prev_denied])
                w.writerow(['Scan success rate (%)', scan_success_rate, prev_rate])
                w.writerow([])
                w.writerow(['Event', 'Check-ins in month'])
                for row in event_stats:
                    w.writerow([row['event_name'], row['check_ins']])
                from django.core.files.base import ContentFile
                report.file.save(
                    f'monthly_report_{month_start.isoformat()}.csv',
                    ContentFile(buf.getvalue().encode('utf-8')),
                    save=True,
                )
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'Could not save file: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created monthly report: {report.id} – {title}'))
