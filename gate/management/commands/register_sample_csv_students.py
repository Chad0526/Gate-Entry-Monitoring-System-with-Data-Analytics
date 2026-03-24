"""Register 50 sample students (20240001–20240050) for demos and CSV import tests.
Usage: python manage.py register_sample_csv_students
Creates students with unique student_id, BST, 1st year, sections A/B/C. Skips any ID that already exists.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from gate.models import Student


class Command(BaseCommand):
    help = 'Register 50 sample students (20240001–20240050). Unique student_id each.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        # 50 students: 20240001 .. 20240050. Sections: 1-17 A, 18-34 B, 35-50 C
        to_create = []
        for i in range(1, 51):
            sid = '2024%04d' % i
            if i <= 17:
                section = 'A'
            elif i <= 34:
                section = 'B'
            else:
                section = 'C'
            sex = Student.SEX_MALE if i % 2 else Student.SEX_FEMALE
            to_create.append({
                'student_id': sid,
                'first_name': 'Sample',
                'last_name': 'Student %d' % i,
                'sex': sex,
                'course': 'BST',
                'year_level': '1',
                'section': section,
                'account_status': Student.ACCOUNT_STATUS_APPROVED,
                'is_active': True,
            })

        existing_ids = set(
            Student.objects.filter(student_id__in=[r['student_id'] for r in to_create]).values_list('student_id', flat=True)
        )
        new_list = [r for r in to_create if r['student_id'] not in existing_ids]
        skipped = len(to_create) - len(new_list)

        if not new_list:
            self.stdout.write(self.style.WARNING(
                'All 50 sample student IDs (20240001–20240050) already exist. Nothing to create.'
            ))
            if skipped:
                self.stdout.write('  All sample IDs already exist — use Gate → Students to manage records.')
            return

        if dry_run:
            self.stdout.write('Would create %d students (skip %d already existing):' % (len(new_list), skipped))
            for r in new_list[:5]:
                self.stdout.write('  %s - %s %s (%s, %s year, Sec %s)' % (
                    r['student_id'], r['first_name'], r['last_name'], r['course'], r['year_level'], r['section']))
            if len(new_list) > 5:
                self.stdout.write('  ... and %d more.' % (len(new_list) - 5))
            return

        try:
            with transaction.atomic():
                for r in new_list:
                    Student.objects.create(
                        student_id=r['student_id'],
                        first_name=r['first_name'],
                        last_name=r['last_name'],
                        sex=r['sex'],
                        course=r['course'],
                        year_level=r['year_level'],
                        section=r['section'],
                        account_status=r['account_status'],
                        is_active=r['is_active'],
                    )
            self.stdout.write(self.style.SUCCESS(
                'Registered %d sample students (20240001–20240050). %s already existed.'
                % (len(new_list), skipped if skipped else 'None')
            ))
            self.stdout.write('  Course: BST, Year: 1st, Sections: A (1–17), B (18–34), C (35–50).')
            self.stdout.write('  Use Gate → Students to review or import additional data via CSV if needed.')
        except Exception as e:
            self.stderr.write(self.style.ERROR('Failed: %s' % e))
            raise
