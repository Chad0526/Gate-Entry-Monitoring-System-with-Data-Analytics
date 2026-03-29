"""Set Student.sex to MALE for every row where sex is blank (legacy / incomplete data).

Usage:
  python manage.py set_blank_student_sex_male --dry-run   # count only
  python manage.py set_blank_student_sex_male             # apply
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from gate.models import Student


class Command(BaseCommand):
    help = 'Set blank student sex/gender to MALE for all matching rows.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print how many rows would change; do not write to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        qs = Student.objects.filter(Q(sex='') | Q(sex__isnull=True))
        n = qs.count()
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Dry run: %s student(s) have blank sex; would set to MALE.' % n)
            )
            return
        updated = qs.update(sex=Student.SEX_MALE)
        self.stdout.write(self.style.SUCCESS('Updated %s student(s) to MALE.' % updated))
