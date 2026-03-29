"""Bulk-set Student.sex from a CSV (student_id, sex). Use when many rows lack gender after a legacy import.

Example CSV:
  student_id,sex
  20240001,MALE
  20240002,f

Usage: python manage.py set_student_sex_from_csv path/to/file.csv [--dry-run]
"""
import csv

from django.core.management.base import BaseCommand

from gate.models import Student


def _normalize_sex(val):
    if not val:
        return ''
    s = str(val).strip().lower()
    if s in ('m', 'male'):
        return Student.SEX_MALE
    if s in ('f', 'female'):
        return Student.SEX_FEMALE
    return ''


class Command(BaseCommand):
    help = 'Set student sex from CSV columns: student_id, sex (MALE/FEMALE or M/F).'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to UTF-8 CSV file')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show changes without saving',
        )

    def handle(self, *args, **options):
        path = options['csv_path']
        dry_run = options['dry_run']
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames_raw = reader.fieldnames
                rows = list(reader)
        except OSError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return
        if not rows:
            self.stdout.write(self.style.WARNING('CSV is empty.'))
            return

        fieldnames = {c.strip().lower() for c in (fieldnames_raw or [])}
        if 'student_id' not in fieldnames and 'id' not in fieldnames:
            self.stderr.write(self.style.ERROR('CSV must have a student_id (or id) column.'))
            return
        if 'sex' not in fieldnames and 'gender' not in fieldnames:
            self.stderr.write(self.style.ERROR('CSV must have a sex (or gender) column.'))
            return

        updated = 0
        missing_id = 0
        bad_sex = 0
        not_found = 0
        for row in rows:
            kr = {(k or '').strip().lower(): v for k, v in row.items()}
            sid = (kr.get('student_id') or kr.get('id') or '').strip()
            raw = kr.get('sex') or kr.get('gender') or ''
            sx = _normalize_sex(raw)
            if not sid:
                missing_id += 1
                continue
            if not sx:
                bad_sex += 1
                continue
            try:
                st = Student.objects.get(student_id=sid)
            except Student.DoesNotExist:
                not_found += 1
                continue
            if st.sex == sx:
                continue
            if dry_run:
                self.stdout.write('Would set %s sex %s -> %s' % (sid, st.sex or '(empty)', sx))
            else:
                st.sex = sx
                st.save(update_fields=['sex'])
            updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no database writes.'))
        self.stdout.write(
            'Done: updated=%s missing_id=%s bad_sex=%s not_found=%s' % (
                updated, missing_id, bad_sex, not_found,
            )
        )
