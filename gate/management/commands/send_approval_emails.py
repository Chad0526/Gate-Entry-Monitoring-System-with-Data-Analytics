"""Send approval notification email to all approved students who have an email.
Useful one-time catch-up so every approved student gets the same message.
Usage: python manage.py send_approval_emails
"""
from django.core.management.base import BaseCommand
from gate.models import Student
from gate.notifications import notify_student_status_change


class Command(BaseCommand):
    help = 'Send approval email to all approved students with an email address'

    def handle(self, *args, **options):
        qs = Student.objects.filter(
            account_status=Student.ACCOUNT_STATUS_APPROVED,
            is_active=True,
        ).exclude(email__isnull=True).exclude(email='')
        total = qs.count()
        sent = 0
        for student in qs:
            try:
                notify_student_status_change(student, new_status=Student.ACCOUNT_STATUS_APPROVED)
                sent += 1
                self.stdout.write(f'Sent to: {student.email}')
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'Skip {student.email}: {e}'))
        self.stdout.write(self.style.SUCCESS(f'Done. Sent {sent} of {total} approval emails.'))
