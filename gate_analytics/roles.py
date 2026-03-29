"""
Role-based access for City College of Bayawan.
Roles: Admin, Faculty, Staff, Student (legacy), Student Affairs (registry / e-ID release).
Gate kiosk: assigned staff/faculty log in; no separate gate-only role.
"""
from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.contrib import messages

ROLE_NAMES = (
    'Admin',
    'Faculty',
    'Staff',
    'Student',
    'Student Affairs',  # Student services: student registry, approve records, print/release e-IDs
)
ROLE_GROUPS = {name.lower(): name for name in ROLE_NAMES}

# When a user has several role groups, pick one deterministically (highest first).
# Ensures e.g. Staff + Student Affairs resolves to student affairs so SAS actions match the sidebar.
ROLE_PRIORITY = (
    'admin',
    'student affairs',
    'staff',
    'faculty',
    'student',
)


def get_user_role(user):
    """Return user's role as lowercase string ('admin','staff', etc.) or None.
    Staff/superuser without a group are treated as 'admin'.

    If the user belongs to more than one known role group, the role with the highest
    ROLE_PRIORITY wins (not ORM iteration order).

    Role lookup is case-insensitive to avoid mismatches when group names
    may be stored with different capitalization.
    """
    if not user or not user.is_authenticated:
        return None
    matched = set()
    for group in user.groups.all():
        lname = group.name.lower()
        if lname in ROLE_GROUPS:
            matched.add(lname)
    if matched:
        for role_slug in ROLE_PRIORITY:
            if role_slug in matched:
                return role_slug
        return next(iter(matched))
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return 'admin'
    return None


def has_reports_access(user):
    """True if user can use full reports, export, and audit (admin, staff, faculty)."""
    role = get_user_role(user)
    return role in ('admin', 'staff', 'faculty')


def role_required(*allowed_roles):
    """
    Decorator: allow access only if user is logged in and has one of allowed_roles.
    allowed_roles: e.g. 'admin', 'staff'
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            role = get_user_role(request.user)
            if role is None:
                messages.error(request, 'Your account has no role. Contact the administrator.')
                return redirect('login')
            if role not in [r.lower() for r in allowed_roles]:
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1><p>You do not have permission to access this page.</p>'
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def has_role(user, *roles):
    """Return True if user has one of the given roles."""
    role = get_user_role(user)
    return role in [r.lower() for r in roles]


class RoleRequiredMixin:
    """CBV mixin: allow access only if user has one of allowed_roles. Set allowed_roles = ['admin','staff']."""
    allowed_roles = ()  # override in subclass

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        role = get_user_role(request.user)
        if role is None:
            messages.error(request, 'Your account has no role. Contact the administrator.')
            return redirect('login')
        roles = [r.lower() for r in self.allowed_roles]
        if role not in roles:
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1><p>You do not have permission to access this page.</p>'
            )
        return super().dispatch(request, *args, **kwargs)


def user_role_context(request):
    """Template context: user_role for sidebar/navbar; profile_avatar_url for sidebar profile photo."""
    if not request.user.is_authenticated:
        return {'user_role': None, 'profile_avatar_url': None}
    try:
        from gate.models import UserProfile
        up = UserProfile.objects.filter(user=request.user).first()
        avatar_url = up.avatar.url if up and up.avatar else None
    except Exception:
        avatar_url = None
    return {
        'user_role': get_user_role(request.user),
        'profile_avatar_url': avatar_url,
    }
