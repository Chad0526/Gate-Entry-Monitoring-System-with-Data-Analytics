"""Template tags for admin notifications (e.g. pending staff/faculty approvals)."""
from django import template
from django.contrib.auth import get_user_model

register = template.Library()


@register.simple_tag
def pending_staff_personnel_approvals_count():
    """Return count of inactive users in Staff or Faculty groups (pending approval)."""
    User = get_user_model()
    return User.objects.filter(
        is_active=False
    ).filter(
        groups__name__in=['Staff', 'Faculty']
    ).distinct().count()
