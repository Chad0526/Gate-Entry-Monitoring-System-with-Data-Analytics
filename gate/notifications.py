"""Email and in-app notifications: denied entry, capacity alert, daily digest, announcements."""
import datetime
import logging
from django.conf import settings
from django.core.mail import send_mail, send_mass_mail, EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)


def _user_accepts_announcement_email(user):
    """
    Who receives org announcement / AdminNotification follow-up emails:
    - Staff/faculty with StaffPersonnelProfile: respect email_notifications_announcements.
    - Admin, Student Affairs, superuser: use User.email when set (no profile required).
    - Staff/faculty without a profile yet: no email (avoid noise until profile exists).
    """
    if not user or not getattr(user, 'is_active', True):
        return False
    email = (getattr(user, 'email', None) or '').strip()
    if not email:
        return False
    try:
        if user.groups.filter(name__iexact='student').exists():
            return False
    except Exception:
        pass
    from gate.models import StaffPersonnelProfile
    try:
        profile = StaffPersonnelProfile.objects.get(user_id=user.pk)
    except StaffPersonnelProfile.DoesNotExist:
        profile = None
    if profile is not None:
        return bool(profile.email_notifications_announcements)
    if getattr(user, 'is_superuser', False):
        return True
    try:
        gnames = {g.name.lower() for g in user.groups.all()}
    except Exception:
        gnames = set()
    return 'admin' in gnames or 'student affairs' in gnames


def send_announcement_emails(users, title, message, subject_prefix=None):
    """
    Send plain-text emails for broadcast AdminNotifications and similar alerts.
    Respects StaffPersonnelProfile opt-in for staff/faculty; always sends to
    Admin / Student Affairs / superuser when User.email is set (operational accounts).
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        site_name = getattr(settings, 'SITE_NAME', 'City College of Bayawan')
        prefix = subject_prefix if subject_prefix is not None else f"[{site_name}] "
        subject = f"{prefix}{title}" if title else f"{prefix}Announcement"

        user_ids = [u.pk for u in users if getattr(u, 'pk', None)]
        if not user_ids:
            return
        user_qs = (
            User.objects.filter(pk__in=user_ids)
            .exclude(groups__name__iexact='student')
            .distinct()
            .prefetch_related('groups')
        )
        recipient_emails = []
        for u in user_qs:
            if _user_accepts_announcement_email(u):
                recipient_emails.append(str(u.email).strip())
        recipient_emails = list(dict.fromkeys(recipient_emails))
        if not recipient_emails:
            return
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        body = message or "(No message body)"
        messages = [(subject, body, from_email, [em]) for em in recipient_emails]
        send_mass_mail(messages, fail_silently=True)
    except Exception as e:
        logger.warning('send_announcement_emails failed: %s', e)


def _get_admin_emails():
    """Emails to receive alerts (from ADMINS or NOTIFICATION_EMAILS)."""
    emails = getattr(settings, 'NOTIFICATION_EMAILS', None)
    if emails:
        return list(emails) if isinstance(emails, (list, tuple)) else [emails]
    return [e[1] for e in getattr(settings, 'ADMINS', [])]


def notify_denied_entry(incident, student_id=None, scanned_id=None):
    """Send email when gate entry is denied (optional)."""
    if not getattr(settings, 'NOTIFY_ON_DENIED_ENTRY', False):
        return
    emails = _get_admin_emails()
    if not emails:
        return
    try:
        subject = f"[Gate] Entry denied – {incident.get_reason_display()}"
        body = (
            f"Time: {timezone.localtime(incident.timestamp).strftime('%Y-%m-%d %H:%M')}\n"
            f"Reason: {incident.get_reason_display()}\n"
            f"Scanned ID: {scanned_id or incident.scanned_id or '—'}\n"
            f"Details: {incident.details or '—'}\n"
        )
        if incident.student_id:
            body += f"Student: {incident.student.student_id} {incident.student.get_full_name()}\n"
        send_mail(
            subject,
            body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost'),
            emails,
            fail_silently=True,
        )
    except Exception as e:
        logger.warning('notify_denied_entry failed: %s', e)


def send_daily_digest(date=None):
    """Send daily digest email to admins (call from management command or cron). Uses local day bounds for timezone correctness."""
    from .models import GateEntry, GateIncident
    from .gate_views import _local_day_bounds
    date = date or timezone.localdate()
    emails = _get_admin_emails()
    if not emails:
        return
    day_start, day_end = _local_day_bounds(date)
    entries = GateEntry.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end)
    granted = entries.filter(granted=True).count()
    denied = entries.filter(granted=False).count()
    incidents = GateIncident.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end).count()
    try:
        subject = f"[Daily digest] Gate & attendance – {date}"
        body = (
            f"Date: {date}\n"
            f"Gate granted: {granted}\n"
            f"Gate denied: {denied}\n"
            f"Incidents: {incidents}\n"
        )
        send_mail(
            subject,
            body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost'),
            emails,
            fail_silently=True,
        )
    except Exception as e:
        logger.warning('send_daily_digest failed: %s', e)


def notify_student_status_change(student, new_status=None):
    """Email the student when their account status changes (active/inactive)."""
    email = (student.email or '').strip()
    if not email:
        return
    try:
        site_name = getattr(settings, 'SITE_NAME', 'City College of Bayawan')
        status_code = new_status or getattr(student, 'account_status', '')
        try:
            status_label = student.get_account_status_display()
        except Exception:
            status_label = status_code or 'Updated'

        subject = f"[{site_name}] Your student account status: {status_label}"

        # Customize message per status (optional).
        status_code_upper = (status_code or '').upper()
        if status_code_upper == 'APPROVED':
            main_line = "Your student account has been approved by the administrator."
            extra_line = "You can now sign in and use the gate & attendance system."
        elif status_code_upper == 'INACTIVE':
            main_line = "Your student account has been set to inactive."
            extra_line = "You will not be able to use the gate & attendance system until it is reactivated."
        else:
            main_line = f"Your student account status has been updated to: {status_label}."
            extra_line = ""

        body_lines = [
            f"Hello {student.get_full_name() or student.student_id},",
            "",
            main_line,
            extra_line,
            "",
            "If you did not request this account, please contact the school immediately.",
        ]
        body = "\n".join(body_lines)

        # Send only to the student. BCC the system sender for audit (so student's inbox is the only To:).
        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
        msg = EmailMessage(
            subject,
            body,
            sender,
            [email],
            bcc=[sender] if sender and sender != email else [],
        )
        msg.send(fail_silently=False)
    except Exception as e:
        logger.warning('notify_student_status_change failed: %s', e)


def notify_student_approved(student):
    """Backward-compatible wrapper: specific case for approval."""
    notify_student_status_change(student, new_status='APPROVED')
