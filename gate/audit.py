"""Audit log: who did what, when."""
from .models import AuditLog


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
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            description=(description or '')[:2000],
            ip_address=ip_address or None,
        )
    except Exception:
        pass
