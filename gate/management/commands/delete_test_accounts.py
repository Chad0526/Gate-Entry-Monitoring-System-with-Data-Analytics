"""
Delete users and students registered with specific email addresses (e.g. old Gmail
accounts you want to reuse). Keeps nierechad2002@gmail.com; use this to remove
test accounts that used your other gmails.

Usage:
  # Preview what would be deleted (dry run):
  python manage.py delete_test_accounts nierechaddistic@gmail.com --dry-run

  # Actually delete those accounts:
  python manage.py delete_test_accounts nierechaddistic@gmail.com

  # Multiple emails:
  python manage.py delete_test_accounts email1@gmail.com email2@gmail.com

  # List all User and Student emails in the DB (to see which to remove):
  python manage.py delete_test_accounts --list
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Delete users and students with the given email addresses (e.g. old gmails to reuse). Use --list to see all emails.'

    def add_arguments(self, parser):
        parser.add_argument(
            'emails',
            nargs='*',
            help='Email address(es) to delete (User and Student with this email).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be deleted; do not delete.',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            dest='list_emails',
            help='List all User and Student emails in the database (then run again with emails to delete).',
        )

    def handle(self, *args, **options):
        if options['list_emails']:
            self._list_emails()
            return

        emails = [e.strip().lower() for e in options['emails'] if e.strip()]
        if not emails:
            self.stderr.write(self.style.WARNING(
                'Provide at least one email to delete, or use --list to see all emails.'
            ))
            return

        keep = 'nierechad2002@gmail.com'
        if keep in emails:
            self.stderr.write(self.style.WARNING(
                f'Ignoring "{keep}" so it is never deleted. Remove it from the list if you only wanted to list.'
            ))
            emails = [e for e in emails if e != keep]
        if not emails:
            return

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN – no changes will be made.'))

        from gate.models import Student

        with transaction.atomic():
            if dry_run:
                self._report_only(emails, User, Student)
            else:
                self._delete_accounts(emails, User, Student)

    def _list_emails(self):
        from gate.models import Student

        self.stdout.write(self.style.HTTP_INFO('--- Users (staff/faculty/guard) ---'))
        for u in User.objects.all().order_by('email'):
            email = (u.email or '').strip()
            if not email:
                email = '(no email)'
            self.stdout.write(f'  {u.username}  {email}')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('--- Students ---'))
        for s in Student.objects.all().order_by('email')[:200]:
            email = (s.email or '').strip()
            if not email:
                email = '(no email)'
            self.stdout.write(f'  {s.student_id}  {s.get_full_name()}  {email}')
        total = Student.objects.count()
        if total > 200:
            self.stdout.write(f'  ... and {total - 200} more students.')

    def _report_only(self, emails, User, Student):
        for email in emails:
            users = list(User.objects.filter(email__iexact=email))
            students = list(Student.objects.filter(email__iexact=email))
            if not users and not students:
                self.stdout.write(self.style.WARNING(f'  {email}: no User or Student found.'))
                continue
            if users:
                self.stdout.write(f'  Would delete User(s): {email}')
                for u in users:
                    self.stdout.write(f'    - {u.username}')
            if students:
                self.stdout.write(f'  Would delete Student(s): {email}')
                for s in students:
                    self.stdout.write(f'    - {s.student_id} {s.get_full_name()}')

    def _delete_accounts(self, emails, User, Student):
        deleted_users = 0
        deleted_students = 0
        for email in emails:
            users = list(User.objects.filter(email__iexact=email))
            students = list(Student.objects.filter(email__iexact=email))
            for u in users:
                u.delete()
                deleted_users += 1
                self.stdout.write(self.style.SUCCESS(f'  Deleted user: {u.username} ({email})'))
            for s in students:
                s.delete()
                deleted_students += 1
                self.stdout.write(self.style.SUCCESS(f'  Deleted student: {s.student_id} {s.get_full_name()} ({email})'))
        self.stdout.write(self.style.SUCCESS(
            f'Done. Deleted {deleted_users} user(s) and {deleted_students} student(s).'
        ))
