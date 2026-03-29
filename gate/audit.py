"""Audit log: who did what, when."""
from django.contrib.auth import get_user_model
from django.db import models

from .models import AuditLog, AdminNotification


def log_action(request, action, model_name='', object_id='', description=''):
    """Record an admin/staff action for audit (from a view with request)."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
    log_action_with_user(user=user, action=action, model_name=model_name, object_id=object_id, description=description, ip_address=ip)


def log_action_with_user(user, action, model_name='', object_id='', description='', ip_address=None):
    """Record an action for audit when request is not available (e.g. signal or background)."""
    if not user or not getattr(user, 'is_authenticated', True):
        return
    uid = getattr(user, 'pk', None)
    if not uid:
        return
    User = get_user_model()
    # Stale session / restored DB: request.user.pk may not exist — never insert bad FK (SQLite fails at commit).
    if not User.objects.filter(pk=uid).exists():
        user = None
    try:
        entry = AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id is not None else '',
            description=(description or '')[:2000],
            ip_address=ip_address or None,
        )
        _notify_admins_of_audit_change(entry)
    except Exception:
        pass


def _notify_admins_of_audit_change(audit_entry):
    """
    Create in-app admin notifications for tracked system changes.
    This gives admin visibility on staff/SAS edits across the app.
    """
    if not audit_entry or not getattr(audit_entry, 'user_id', None):
        return
    User = get_user_model()
    admins = User.objects.filter(
        is_active=True,
    ).filter(
        models.Q(groups__name__iexact='admin')
        | models.Q(is_superuser=True)
        | models.Q(is_staff=True)
    ).distinct()
    actor = audit_entry.user
    actor_name = (actor.get_full_name() or '').strip() or actor.username
    model_label = (audit_entry.model_name or 'System').strip() or 'System'
    action_label = (audit_entry.action or 'updated').replace('_', ' ').strip()
    object_label = f" #{audit_entry.object_id}" if (audit_entry.object_id or '').strip() else ''
    msg = (
        f'{actor_name} performed "{action_label}" on {model_label}{object_label}.\n'
        f'Details: {(audit_entry.description or "—")[:600]}'
    )
    for admin in admins:
        AdminNotification.objects.create(
            notification_type='system',
            priority='normal',
            title=f'System change: {model_label}',
            message=msg[:1000],
            target_user=admin,
            broadcast=False,
        )
