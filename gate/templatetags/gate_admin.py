"""Template tags for admin notifications (e.g. pending staff/faculty/guard approvals)."""
from django import template
from django.contrib.auth import get_user_model

register = template.Library()


@register.simple_tag
def pending_staff_guard_approvals_count():
    """Return count of inactive users in Staff, Faculty, or Guard groups (pending approval)."""
    User = get_user_model()
    return User.objects.filter(
        is_active=False
    ).filter(
        groups__name__in=['Staff', 'Faculty', 'Guard']
    ).distinct().count()
