"""
Rewrite existing AdminNotification rows to shorter titles/messages (matches current app copy).

Rebuilds from related_student / related_incident when possible; otherwise truncates safely.

Usage:
  python manage.py compact_admin_notifications
  python manage.py compact_admin_notifications --dry-run
  python manage.py compact_admin_notifications --only-type incident
"""

import re

from django.core.management.base import BaseCommand
from django.urls import reverse

from gate.models import AdminNotification


def _truncate_text(s, max_len, ellipsis='…'):
    if s is None:
        return s
    s = str(s).strip()
    if len(s) <= max_len:
        return s
    cut = s[: max_len + 1].rsplit(' ', 1)[0].strip()
    if len(cut) < max_len // 2:
        cut = s[:max_len].rstrip()
    return cut + ellipsis


class Command(BaseCommand):
    help = 'Compact stored admin notification titles and messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show counts and samples only; do not save.',
        )
        parser.add_argument(
            '--only-type',
            default='',
            help='Limit to one notification_type (e.g. incident, system).',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        qs = AdminNotification.objects.select_related(
            'related_student',
            'related_incident',
            'related_incident__student',
        ).order_by('pk')
        if options['only_type']:
            qs = qs.filter(notification_type=options['only_type'].strip())

        updated = 0
        scanned = 0
        for notif in qs.iterator(chunk_size=200):
            scanned += 1
            new_title, new_msg = self._compact_one(notif)
            if new_title == notif.title and new_msg == notif.message:
                continue
            updated += 1
            if dry:
                if updated <= 5:
                    self.stdout.write(
                        f'  #{notif.pk} [{notif.notification_type}] title: {notif.title[:60]}… → {new_title[:60]}…'
                    )
                continue
            notif.title = new_title[:200]
            notif.message = new_msg[:1000]
            notif.save(update_fields=['title', 'message'])

        self.stdout.write(f'Scanned: {scanned}  Would update / updated: {updated}')
        if dry:
            self.stdout.write(self.style.WARNING('Dry run — no database writes.'))

    def _compact_one(self, notif):
        t = notif.notification_type
        title, msg = notif.title, notif.message or ''

        try:
            list_path = reverse('gate-incident-list')
        except Exception:
            list_path = '/gate/incidents/'

        if t in ('sas_inactive_ready_activation', 'sas_verified_gate_followup'):
            st = notif.related_student
            inc = notif.related_incident
            if st and inc:
                note = (inc.details or '—').strip() or '—'
                if len(note) > 200:
                    note = note[:200] + '…'
                try:
                    st_path = reverse('gate-student-edit', kwargs={'pk': st.pk})
                except Exception:
                    st_path = ''
                if t == 'sas_inactive_ready_activation':
                    title = f'Activate account: {st.student_id}'
                    msg = (
                        f'SAS cleared {st.get_full_name()} ({st.student_id}). '
                        f'Account still inactive — activate in profile.\n'
                        f'Note: {note}\n'
                        f'{list_path}'
                    )
                    if st_path:
                        msg += f'\n{st_path}'
                else:
                    title = f'SAS cleared: {st.student_id} (active)'
                    msg = (
                        f'SAS cleared {st.get_full_name()} ({st.student_id}). '
                        f'Account already active — FYI only.\n'
                        f'Note: {note}\n'
                        f'{list_path}'
                    )
                return title, msg
            return _truncate_text(title, 100), _truncate_text(msg, 450)

        if t == 'incident' and notif.related_incident_id:
            inc = notif.related_incident
            if inc:
                reason_display = inc.get_reason_display()
                student_info = (
                    inc.student.get_full_name() if inc.student else (inc.scanned_id or '—')
                )
                det = (inc.details or '—').strip() or '—'
                if len(det) > 220:
                    det = det[:220] + '…'
                title = f'Incident: {reason_display}'
                msg = f'{reason_display} • {student_info}\nNote: {det}\n{list_path}'
                return title, msg
            return _truncate_text(title, 100), _truncate_text(msg, 450)

        if t == 'student_registration' and notif.related_student_id:
            st = notif.related_student
            if st:
                title = f'New student: {st.student_id}'
                msg = (
                    f'{st.get_full_name()} ({st.student_id}) — self-registered; '
                    f'verify records, then activate.'
                )
                return title, msg
            return _truncate_text(title, 100), _truncate_text(msg, 400)

        if t == 'gate_manual_referral' and notif.related_student_id:
            st = notif.related_student
            if st:
                old_prefixes = ('Guard manual entry — ', 'Manual entry: ')
                label = title
                for p in old_prefixes:
                    if label.startswith(p):
                        label = label[len(p) :].strip()
                        break
                label = (label or 'Office referral').strip()[:100]
                try:
                    st_path = reverse('gate-student-edit', kwargs={'pk': st.pk})
                except Exception:
                    st_path = ''
                title = f'Manual entry: {label}'
                actor_name = 'Gate staff'
                m = re.search(r'Recorded by:\s*([^\n]+)', msg, re.I)
                if m:
                    actor_name = m.group(1).strip()[:120]
                msg = (
                    f'{st.get_full_name()} ({st.student_id}) • Route: {label}\n'
                    f'By: {actor_name}\n'
                    f'Unresolved? You may mark inactive from the student profile.\n'
                )
                if st_path:
                    msg += f'{st_path}\n'
                msg += f'{list_path}\n'
                return title, msg
            return _truncate_text(title, 100), _truncate_text(msg, 450)

        if t == 'staff_personnel_registration':
            return _truncate_text(title, 120), _truncate_text(msg, 380)

        if t == 'system':
            tit = (title or 'System').replace('System change: ', '').strip() or 'System'
            body = msg or ''
            if 'performed "' in body.lower():
                body = re.sub(
                    r'\s+performed\s+"([^"]+)"\s+on\s+',
                    r' → \1 on ',
                    body,
                    count=1,
                    flags=re.IGNORECASE,
                )
                body = re.sub(r'\nDetails:\s*', '\n', body, count=1, flags=re.IGNORECASE)
            return _truncate_text(tit, 100), _truncate_text(body.strip(), 360)

        if t in ('capacity', 'personnel_alert'):
            return _truncate_text(title, 120), _truncate_text(msg, 400)

        return _truncate_text(title, 120), _truncate_text(msg, 450)
