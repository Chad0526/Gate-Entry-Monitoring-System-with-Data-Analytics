"""
Guard monitor (token-only embed): manual incident reports → GateIncident + office routing.

Routing (configure Django Groups and/or direct emails in settings / .env):
- id_issue (ID mismatch, wrong person, suspicious ID) → Student Affairs (SAS) group + optional emails
- not_registered → Registrar group + optional emails
- other → both offices (union of SAS + Registrar targets)

When office group users are matched, app admins (admin portal / superuser) also receive the same
in-app incident row so they see ID mismatches immediately, not only after SAS marks checked.

If no users match the configured groups, falls back to broadcast AdminNotification (staff/admin)
when GATE_GUARD_INCIDENT_FALLBACK_BROADCAST is True, and emails NOTIFICATION_EMAILS.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


def _split_csv(s):
    if not s:
        return []
    return [x.strip() for x in str(s).split(',') if x.strip()]


def users_in_named_groups(comma_separated_group_names):
    """Active non-student users in any Group whose name matches (case-insensitive)."""
    names = _split_csv(comma_separated_group_names)
    if not names:
        return User.objects.none()
    q = Q()
    for name in names:
        q |= Q(groups__name__iexact=name)
    return (
        User.objects.filter(q)
        .exclude(groups__name__iexact='student')
        .filter(is_active=True)
        .distinct()
    )


def create_guard_incident_and_notify(category, details='', scanned_id='', ip_address=None):
    """
    Create GateIncident and notify SAS / Registrar / both per category.

    category: 'id_issue' | 'not_registered' | 'other'
    """
    from gate.models import GateIncident, AuditLog, AdminNotification, Student
    from gate.admin_notification_service import AdminNotificationService

    reason_map = {
        'id_issue': 'identity_mismatch',
        'not_registered': 'not_registered',
        'other': 'other',
    }
    reason = reason_map.get(category, 'other')
    details = (details or '').strip()[:2000]
    scanned_id = (scanned_id or '').strip()[:100]

    student = None
    if scanned_id:
        student = Student.objects.filter(student_id__iexact=scanned_id).first()

    auto_verified = False
    auto_verified_note = ''
    auto_verified_by = None
    if reason == 'identity_mismatch' and student is not None:
        last_verified = (
            GateIncident.objects.filter(
                student=student,
                reason='identity_mismatch',
                sas_review_status='verified',
            )
            .exclude(sas_checked_at__isnull=True)
            .select_related('sas_checked_by')
            .order_by('-sas_checked_at')
            .first()
        )
        if last_verified is not None:
            auto_verified = True
            auto_verified_by = last_verified.sas_checked_by
            auto_verified_note = (
                f'Auto-checked: student previously verified by SAS'
                f' on {timezone.localtime(last_verified.sas_checked_at).strftime("%Y-%m-%d %H:%M")}.'
            )

    incident = GateIncident.objects.create(
        student=student,
        reason=reason,
        details=details or f'Guard report ({category}).',
        scanned_id=scanned_id,
        staff_alerted=True,
        sas_review_status='verified' if auto_verified else 'to_check',
        sas_checked_by=auto_verified_by,
        sas_checked_at=timezone.now() if auto_verified else None,
        sas_check_notes=auto_verified_note,
    )

    sas_groups = getattr(settings, 'GATE_GUARD_INCIDENT_GROUPS_SAS', '') or ''
    reg_groups = getattr(settings, 'GATE_GUARD_INCIDENT_GROUPS_REGISTRAR', '') or ''
    emails_sas = _split_csv(getattr(settings, 'GATE_GUARD_INCIDENT_EMAILS_SAS', '') or '')
    emails_reg = _split_csv(getattr(settings, 'GATE_GUARD_INCIDENT_EMAILS_REGISTRAR', '') or '')
    fallback_broadcast = getattr(settings, 'GATE_GUARD_INCIDENT_FALLBACK_BROADCAST', True)

    if category == 'id_issue':
        office_label = 'Student Affairs (SAS) — ID / identity issues'
        target_users = users_in_named_groups(sas_groups)
        extra_emails = emails_sas
    elif category == 'not_registered':
        office_label = 'Registrar — registration / enrollment'
        target_users = users_in_named_groups(reg_groups)
        extra_emails = emails_reg
    else:
        office_label = 'Student Affairs & Registrar — general incident'
        target_users = (
            users_in_named_groups(sas_groups) | users_in_named_groups(reg_groups)
        ).distinct()
        extra_emails = list({*emails_sas, *emails_reg})

    site = getattr(settings, 'SITE_NAME', 'Gate')
    ts = timezone.localtime(incident.timestamp).strftime('%Y-%m-%d %H:%M')
    title = f'Guard incident: {incident.get_reason_display()}'
    det = (details or '—').strip() or '—'
    if len(det) > 200:
        det = det[:200] + '…'
    body = (
        f'{ts} • {office_label}\n'
        f'ID {scanned_id or "—"} • #{incident.id}\n'
        f'{det}\n'
        f'IP: {ip_address or "—"}'
    )

    notified_user_ids = set()
    notified_count = 0
    for u in target_users:
        AdminNotification.objects.create(
            notification_type='incident',
            priority='urgent',
            title=title,
            message=body,
            target_user=u,
            broadcast=False,
            related_incident=incident,
        )
        notified_user_ids.add(u.pk)
        notified_count += 1

    if notified_count > 0:
        try:
            for admin_u in AdminNotificationService._users_app_admin_portal():
                if admin_u.pk in notified_user_ids:
                    continue
                AdminNotification.objects.create(
                    notification_type='incident',
                    priority='urgent',
                    title=title,
                    message=body,
                    target_user=admin_u,
                    broadcast=False,
                    related_incident=incident,
                )
        except Exception as e:
            logger.warning('guard incident admin portal notify failed: %s', e)

    if notified_count == 0 and fallback_broadcast:
        try:
            AdminNotificationService.create_notification(
                notification_type='incident',
                title=title,
                message=body + '\n\n(No office group users — sent to Admin & SAS.)',
                priority='urgent',
                broadcast=True,
                related_incident=incident,
            )
        except Exception as e:
            logger.warning('guard incident fallback broadcast failed: %s', e)

    # Email: office addresses + matched users + global alert list
    email_set = set(extra_emails)
    for u in target_users:
        em = getattr(u, 'email', None)
        if em and str(em).strip():
            email_set.add(str(em).strip())
    if not email_set:
        for e in getattr(settings, 'NOTIFICATION_EMAILS', None) or []:
            e = (e or '').strip()
            if e:
                email_set.add(e)

    if email_set:
        try:
            send_mail(
                f'[{site}] {title}',
                body,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost'),
                sorted(email_set),
                fail_silently=True,
            )
        except Exception as e:
            logger.warning('guard incident send_mail failed: %s', e)

    try:
        AuditLog.objects.create(
            user=None,
            action='guard_incident_report',
            model_name='GateIncident',
            object_id=str(incident.id),
            description=f'category={category} routing={office_label[:80]}',
            ip_address=ip_address if _valid_ip(ip_address) else None,
        )
    except Exception as e:
        logger.warning('guard incident audit log failed: %s', e)

    return incident


def _valid_ip(ip):
    if not ip:
        return False
    s = str(ip).strip()[:45]
    try:
        from ipaddress import ip_address
        ip_address(s)
        return True
    except ValueError:
        return False
