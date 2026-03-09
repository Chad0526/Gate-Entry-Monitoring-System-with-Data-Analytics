"""
Context processors for navbar and global template data.
"""
from gate_analytics.roles import get_user_role
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta


def notifications_context(request):
    """
    Add notification counts and items for the navbar: pending approvals, upcoming events,
    new events (recently created). Unread count includes summary rows and each item so
    the badge shows "notifications still to be opened".
    """
    pending_students_count = 0
    pending_students = []
    upcoming_events_count = 0
    upcoming_events = []
    new_events_count = 0
    new_events = []

    if request.user.is_authenticated:
        role = get_user_role(request.user)
        # Student approvals: admin only (not staff)
        if role == 'admin':
            from gate.models import Student
            pending_students = list(
                Student.objects.filter(
                    account_status=Student.ACCOUNT_STATUS_PENDING
                ).order_by('-created_at')[:10]
            )
            pending_students_count = Student.objects.filter(
                account_status=Student.ACCOUNT_STATUS_PENDING
            ).count()

        # Events: admin, staff, and faculty
        if role in ('admin', 'staff', 'faculty'):
            from gate.models import Event

            today = timezone.localdate()
            now = timezone.now()

            # Upcoming: start_date in next 30 days
            until = today + timedelta(days=30)
            upcoming_qs = Event.objects.filter(
                start_date__gte=today,
                start_date__lte=until,
                status__in=('scheduled', 'active'),
            )
            upcoming_events = list(upcoming_qs.order_by('start_date')[:5])
            upcoming_events_count = upcoming_qs.count()

            # New: created in last 7 days (any status)
            new_since = now - timedelta(days=7)
            new_qs = Event.objects.filter(created_date__gte=new_since).order_by('-created_date')
            new_events = list(new_qs[:5])
            new_events_count = new_qs.count()

    total_notifications_count = (
        int(pending_students_count or 0)
        + int(upcoming_events_count or 0)
        + int(new_events_count or 0)
    )
    read_notification_ids = []
    read_student_pks = set()
    read_event_pks = set()
    if request.user.is_authenticated:
        from gate.models import NotificationRead
        read_notification_ids = list(
            NotificationRead.objects.filter(user=request.user)
            .values_list('notification_key', flat=True)
        )
        for rid in read_notification_ids:
            if isinstance(rid, str) and rid.startswith('notif_student_'):
                try:
                    read_student_pks.add(int(rid.replace('notif_student_', '')))
                except ValueError:
                    pass
            elif isinstance(rid, str) and rid.startswith('notif_event_'):
                try:
                    read_event_pks.add(int(rid.replace('notif_event_', '')))
                except ValueError:
                    pass

    # Unread = summary rows (pending, upcoming, new) + each item not yet opened
    unread_notifications_count = 0
    if pending_students_count and 'notif_pending_students' not in read_notification_ids:
        unread_notifications_count += 1
    for s in pending_students:
        if s.pk not in read_student_pks:
            unread_notifications_count += 1
    if upcoming_events_count and 'notif_upcoming_events' not in read_notification_ids:
        unread_notifications_count += 1
    for e in upcoming_events:
        if e.pk not in read_event_pks:
            unread_notifications_count += 1
    if new_events_count and 'notif_new_events' not in read_notification_ids:
        unread_notifications_count += 1
    for e in new_events:
        if e.pk not in read_event_pks:
            unread_notifications_count += 1

    NOTIFICATION_DROPDOWN_MAX = 8
    notification_all = []
    if request.user.is_authenticated and (
        pending_students or upcoming_events or new_events
    ):
        try:
            pending_url = reverse('gate-student-list') + '?pending=1'
            events_url = reverse('event-list')
        except Exception:
            pending_url = '#'
            events_url = '#'

        if pending_students_count:
            notification_all.append({
                'type': 'pending_summary',
                'url': pending_url,
                'label': f'{pending_students_count} student(s) pending approval',
                'label_right': 'Review',
                'icon': 'fa-user-clock',
                'is_read': 'notif_pending_students' in read_notification_ids,
            })
        for s in pending_students:
            notification_all.append({
                'type': 'student',
                'url': reverse('gate-student-edit', kwargs={'pk': s.pk}) + '?from=pending',
                'label': f'{s.get_full_name()} ({s.student_id})',
                'label_right': '',
                'icon': 'fa-user-plus',
                'is_read': s.pk in read_student_pks,
                'obj': s,
            })

        if new_events_count:
            notification_all.append({
                'type': 'new_events_summary',
                'url': events_url,
                'label': f'{new_events_count} new event(s)',
                'label_right': 'View',
                'icon': 'fa-calendar-plus',
                'is_read': 'notif_new_events' in read_notification_ids,
            })
        for e in new_events:
            notification_all.append({
                'type': 'event',
                'url': reverse('event-detail', kwargs={'pk': e.pk}),
                'label': e.name,
                'label_right': f'New · {e.start_date}',
                'icon': 'fa-bullhorn',
                'is_read': e.pk in read_event_pks,
                'obj': e,
            })

        if upcoming_events_count:
            notification_all.append({
                'type': 'events_summary',
                'url': events_url,
                'label': f'{upcoming_events_count} upcoming event(s)',
                'label_right': 'View',
                'icon': 'fa-calendar-alt',
                'is_read': 'notif_upcoming_events' in read_notification_ids,
            })
        for e in upcoming_events:
            # Avoid duplicate entry if same event is in new_events
            if any(i.get('obj') and getattr(i['obj'], 'pk', None) == e.pk for i in notification_all):
                continue
            notification_all.append({
                'type': 'event',
                'url': reverse('event-detail', kwargs={'pk': e.pk}),
                'label': e.name,
                'label_right': str(e.start_date),
                'icon': 'fa-bullhorn',
                'is_read': e.pk in read_event_pks,
                'obj': e,
            })
    notification_has_more = len(notification_all) > NOTIFICATION_DROPDOWN_MAX

    # Check if user is clocked in (for guard role)
    user_clocked_in = False
    if request.user.is_authenticated and request.user.groups.filter(name='Guard').exists():
        from gate.models import GuardShift
        user_clocked_in = GuardShift.objects.filter(
            guard=request.user,
            shift_end__isnull=True
        ).exists()

    return {
        'pending_students_count': pending_students_count,
        'pending_students': pending_students,
        'upcoming_events_count': upcoming_events_count,
        'upcoming_events': upcoming_events,
        'new_events_count': new_events_count,
        'new_events': new_events,
        'total_notifications_count': total_notifications_count,
        'unread_notifications_count': unread_notifications_count,
        'read_notification_ids': read_notification_ids,
        'read_student_pks': read_student_pks,
        'read_event_pks': read_event_pks,
        'notification_all': notification_all,
        'notification_dropdown_max': NOTIFICATION_DROPDOWN_MAX,
        'notification_has_more': notification_has_more,
        'user_clocked_in': user_clocked_in,
    }


def theme_context(request):
    """Inject site theme (name, logo, primary color) for theming."""
    try:
        from gate.models import SiteTheme
        theme = SiteTheme.objects.first()
        if theme:
            return {
                'site_theme': theme,
                'site_name': theme.site_name,
                'site_primary_color': theme.primary_color or '#28a745',
                'site_logo': theme.logo,
            }
    except Exception:
        pass
    return {
        'site_theme': None,
        'site_name': 'City College of Bayawan',
        'site_primary_color': '#28a745',
        'site_logo': None,
    }



def guard_notifications_context(request):
    """
    Add guard-specific notifications to context for navbar.
    Only active for authenticated users in the Guard group.
    """
    if not request.user.is_authenticated:
        return {
            'guard_notifications': [],
            'guard_unread_count': 0,
            'guard_has_urgent': False,
        }
    
    # Check if user is in Guard group
    if not request.user.groups.filter(name='Guard').exists():
        return {
            'guard_notifications': [],
            'guard_unread_count': 0,
            'guard_has_urgent': False,
        }
    
    # Get unread notifications for current guard
    from gate.guard_services import GuardNotificationService
    from django.db.models import Case, When
    
    now = timezone.now()
    from gate.models import GuardNotification
    from django.db.models import Q
    
    # Base queryset for unread notifications
    unread_base = GuardNotification.objects.filter(
        target_guard=request.user,
        is_read=False
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    
    # Calculate unread count
    unread_count = unread_base.count()
    
    # Check for urgent notifications (before slicing)
    has_urgent = unread_base.filter(priority='urgent').exists()
    
    # Get limited list for display (slice at the end)
    unread_notifications = unread_base.order_by(
        # Order by priority (urgent, high, medium, low)
        Case(
            When(priority='urgent', then=0),
            When(priority='high', then=1),
            When(priority='medium', then=2),
            When(priority='low', then=3),
            default=4
        ),
        '-created_at'
    )[:10]  # Limit to 10 most recent unread
    
    return {
        'guard_notifications': list(unread_notifications),
        'guard_unread_count': unread_count,
        'guard_has_urgent': has_urgent,
    }
