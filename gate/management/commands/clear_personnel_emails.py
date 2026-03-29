"""
Clear User.email for staff/faculty/guard accounts so addresses can be reused.

Usage:
  python manage.py clear_personnel_emails --dry-run   # list only
  python manage.py clear_personnel_emails             # apply
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

# Gate / college personnel (not students). Case-insensitive group names.
PERSONNEL_GROUP_NAMES = ('staff', 'faculty', 'guard')


class Command(BaseCommand):
    help = 'Clear email on User accounts in staff/faculty/guard groups (for reusing addresses).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which users would be updated; do not save.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        q = Q()
        for name in PERSONNEL_GROUP_NAMES:
            q |= Q(groups__name__iexact=name)
        qs = User.objects.filter(q).distinct().order_by('username')
        total_in_groups = qs.count()
        if total_in_groups == 0:
            self.stdout.write(self.style.WARNING(
                f'No users belong to any of these groups: {", ".join(PERSONNEL_GROUP_NAMES)}.'
            ))
            return

        with_email = [u for u in qs if (u.email or '').strip()]
        if not with_email:
            self.stdout.write(self.style.WARNING(
                f'{total_in_groups} user(s) in personnel groups, but none have an email set (nothing to clear).'
            ))
            return

        self.stdout.write(self.style.HTTP_INFO(f'Users with email to clear ({len(with_email)}):'))
        for u in with_email:
            self.stdout.write(f'  {u.username!r}  <{u.email}>')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no changes. Run without --dry-run to clear emails.'))
            return

        n = User.objects.filter(pk__in=[u.pk for u in with_email]).update(email='')
        self.stdout.write(self.style.SUCCESS(f'Cleared email on {n} user(s).'))
