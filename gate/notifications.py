"""Email and in-app notifications: denied entry, capacity alert, daily digest."""
import datetime
import logging
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)


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


def notify_capacity_alert(event, current_count, capacity):
    """Send email when event reaches 80% capacity (once per event)."""
    if not getattr(settings, 'NOTIFY_ON_CAPACITY_ALERT', True):
        return
    if event.capacity_alert_sent_at:
        return
    if capacity <= 0:
        return
    pct = 100.0 * current_count / capacity
    if pct < 80:
        return
    emails = _get_admin_emails()
    if not emails:
        return
    try:
        subject = f"[Event] Capacity alert – {event.name} at {pct:.0f}%"
        body = (
            f"Event: {event.name}\n"
            f"Current inside: {current_count}\n"
            f"Capacity: {capacity}\n"
            f"Reached {pct:.1f}%.\n"
        )
        send_mail(
            subject,
            body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost'),
            emails,
            fail_silently=True,
        )
        event.capacity_alert_sent_at = timezone.now()
        event.save(update_fields=['capacity_alert_sent_at'])
    except Exception as e:
        logger.warning('notify_capacity_alert failed: %s', e)


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
    """Email the student when their account status changes (pending, approved, rejected, inactive)."""
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
        elif status_code_upper == 'PENDING':
            main_line = "Your student registration is received and is pending approval."
            extra_line = "You will receive another email once the administrator approves your account."
        elif status_code_upper == 'REJECTED':
            main_line = "Your student account request was not approved."
            extra_line = "Please contact the school for more details if you believe this is a mistake."
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
