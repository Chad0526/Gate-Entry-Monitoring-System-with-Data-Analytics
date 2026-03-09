"""Send daily digest email to admins. Run via cron e.g. 8:00 AM.
Usage: python manage.py send_daily_digest [--date YYYY-MM-DD]
"""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from gate.notifications import send_daily_digest


class Command(BaseCommand):
    help = 'Send daily digest email (gate granted/denied, incidents) to admins'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, default=None, help='Date (YYYY-MM-DD). Default: yesterday.')

    def handle(self, *args, **options):
        if options['date']:
            try:
                from datetime import datetime
                date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR('Invalid --date. Use YYYY-MM-DD.'))
                return
        else:
            date = timezone.localdate() - datetime.timedelta(days=1)
        send_daily_digest(date=date)
        self.stdout.write(self.style.SUCCESS(f'Sent daily digest for {date}.'))
