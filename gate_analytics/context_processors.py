"""
Context processors for navbar and global template data.
"""
from gate_analytics.roles import get_user_role
from django.utils import timezone
from django.utils.translation import gettext as _, ngettext
from django.urls import reverse
from datetime import timedelta


def notification_relative_time(created_at):
    """Short relative time for notification dropdown (seconds → days)."""
    if not created_at:
        return ''
    now = timezone.now()
    created = created_at
    if timezone.is_naive(created):
        created = timezone.make_aware(created, timezone.get_current_timezone())
    if created > now:
        return _('Just now')
    seconds = int((now - created).total_seconds())
    if seconds < 45:
        s = max(1, seconds)
        return ngettext('%(n)d second ago', '%(n)d seconds ago', s) % {'n': s}
    if seconds < 3600:
        m = max(1, seconds // 60)
        return ngettext('%(n)d minute ago', '%(n)d minutes ago', m) % {'n': m}
    if seconds < 86400:
        h = seconds // 3600
        return ngettext('%(n)d hour ago', '%(n)d hours ago', h) % {'n': h}
    d = seconds // 86400
    return ngettext('%(n)d day ago', '%(n)d days ago', d) % {'n': d}


def _append_unread_incident_nav_items(notification_all, user):
    """One navbar row per unread incident AdminNotification (deep-link to incident list)."""
    from gate.models import AdminNotification

    items = list(
        AdminNotification.objects.filter(
            target_user=user,
            is_read=False,
            notification_type='incident',
            related_incident_id__isnull=False,
        )
        .select_related('related_incident', 'related_incident__student')
        .order_by('-created_at')[:15]
    )
    try:
        inc_base = reverse('gate-incident-list')
    except Exception:
        inc_base = '#'
    for j, notif in enumerate(items):
        ri = notif.related_incident
        if not ri:
            continue
        who = ri.student.get_full_name() if ri.student else (ri.scanned_id or '—')
        label = f'{ri.get_reason_display()} — {who}'
        inc_url = f'{inc_base}?highlight={ri.pk}' if inc_base != '#' else '#'
        notification_all.append(
            {
                'type': 'admin_incident_item',
                'url': inc_url,
                'label': label,
                'label_right': _('View'),
                'icon': 'fa-exclamation-triangle',
                'is_read': False,
                'time_ago': notification_relative_time(notif.created_at),
                'show_incident_section': j == 0,
            }
        )


def notifications_context(request):
    """
    Add notification counts and items for the navbar: staff/faculty pending approval,
    upcoming events, new events (recently created). Unread count includes summary rows
    and each item so the badge shows "notifications still to be opened".
    """
    pending_students_count = 0
    pending_students = []
    pending_staff_personnel_count = 0
    pending_staff_personnel = []
    upcoming_events_count = 0
    upcoming_events = []
    new_events_count = 0
    new_events = []

    if request.user.is_authenticated:
        try:
            role = get_user_role(request.user)
            # Staff/Faculty/Personnel pending approval: admin and staff can see and approve
            # Use id subquery so distinct + order_by works on both MySQL and PostgreSQL
            if role in ('admin', 'staff'):
                from django.contrib.auth import get_user_model
                from django.db.models import Q
                User = get_user_model()
                staff_personnel_ids = User.objects.filter(
                    Q(groups__name__iexact='staff') |
                    Q(groups__name__iexact='faculty') |
                    Q(groups__name__iexact='Student Affairs')
                ).distinct().values_list('id', flat=True)
                pending_staff_personnel = list(
                    User.objects.filter(is_active=False, id__in=staff_personnel_ids)
                    .order_by('-date_joined')[:10]
                )
                pending_staff_personnel_count = User.objects.filter(
                    is_active=False, id__in=staff_personnel_ids
                ).count()

            # Events: admin, staff, faculty, and personnel (gate role can see announcements/upcoming events)
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
        except Exception:
            pass

    admin_incident_unread_count = 0
    admin_incident_only_count = 0
    admin_student_reg_unread_count = 0
    admin_staff_reg_unread_count = 0
    admin_sas_unread_notifications = []
    if request.user.is_authenticated:
        try:
            _nr_role = get_user_role(request.user)
            # Ops bell: admin & SAS — not staff/faculty (gate duty)
            if _nr_role in ('admin', 'student affairs'):
                from django.db.models import Q
                from gate.models import AdminNotification
                if _nr_role == 'admin':
                    admin_incident_only_count = AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='incident',
                    ).count()
                    admin_student_reg_unread_count = AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='student_registration',
                    ).count()
                    admin_staff_reg_unread_count = AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='staff_personnel_registration',
                    ).count()
                    admin_sas_unread_notifications = list(
                        AdminNotification.objects.filter(
                            target_user=request.user,
                            is_read=False,
                            notification_type='sas_inactive_ready_activation',
                            related_student_id__isnull=False,
                        ).select_related('related_student').order_by('-created_at')[:15]
                    )
                    type_filter = (
                        Q(notification_type='incident')
                        | Q(notification_type='sas_inactive_ready_activation')
                        | Q(notification_type='student_registration')
                        | Q(notification_type='staff_personnel_registration')
                    )
                else:
                    admin_incident_only_count = AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='incident',
                    ).count()
                    admin_student_reg_unread_count = AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='student_registration',
                    ).count()
                    type_filter = Q(notification_type='incident') | Q(
                        notification_type='student_registration'
                    )
                admin_incident_unread_count = AdminNotification.objects.filter(
                    target_user=request.user,
                    is_read=False,
                ).filter(type_filter).count()
        except Exception:
            pass

    total_notifications_count = (
        int(pending_staff_personnel_count or 0)
        + int(upcoming_events_count or 0)
        + int(new_events_count or 0)
        + int(admin_incident_unread_count or 0)
    )
    read_notification_ids = []
    read_student_pks = set()
    read_staff_personnel_pks = set()
    read_event_pks = set()
    if request.user.is_authenticated:
        try:
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
                elif isinstance(rid, str) and rid.startswith('notif_staff_personnel_'):
                    try:
                        read_staff_personnel_pks.add(int(rid.replace('notif_staff_personnel_', '')))
                    except ValueError:
                        pass
        except Exception:
            pass

    # Unread = summary rows (staff pending, upcoming, new) + each item not yet opened
    unread_notifications_count = 0
    if pending_staff_personnel_count and 'notif_pending_staff_personnel' not in read_notification_ids:
        unread_notifications_count += 1
    for u in pending_staff_personnel:
        if u.pk not in read_staff_personnel_pks:
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

    unread_notifications_count += int(admin_incident_unread_count or 0)

    latest_pending_staff_joined = None
    if pending_staff_personnel:
        latest_pending_staff_joined = max(u.date_joined for u in pending_staff_personnel)
    latest_new_event_created = None
    if new_events:
        latest_new_event_created = max(e.created_date for e in new_events)
    latest_upcoming_event_created = None
    if upcoming_events:
        latest_upcoming_event_created = max(e.created_date for e in upcoming_events)

    NOTIFICATION_DROPDOWN_MAX = 8
    notification_all = []
    if request.user.is_authenticated:
        _nr_for_notif = get_user_role(request.user)
        if _nr_for_notif == 'admin' and (
            admin_sas_unread_notifications
            or admin_incident_only_count
            or admin_student_reg_unread_count
            or admin_staff_reg_unread_count
        ):
            for i, notif in enumerate(admin_sas_unread_notifications):
                st = notif.related_student
                if not st:
                    continue
                try:
                    st_url = reverse('gate-student-edit', kwargs={'pk': st.pk})
                except Exception:
                    st_url = '#'
                notification_all.append({
                    'type': 'admin_sas_activation_student',
                    'url': st_url,
                    'label': f'{st.get_full_name()} ({st.student_id})',
                    'label_right': _('Open profile'),
                    'icon': 'fa-user-check',
                    'is_read': False,
                    'show_sas_section': i == 0,
                    'time_ago': notification_relative_time(notif.created_at),
                })
            if admin_student_reg_unread_count:
                admin_student_reg_items = list(
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='student_registration',
                        related_student_id__isnull=False,
                    ).select_related('related_student').order_by('-created_at')[:15]
                )
                try:
                    st_base = reverse('gate-student-list')
                except Exception:
                    st_base = '#'
                for j, notif in enumerate(admin_student_reg_items):
                    st = notif.related_student
                    if not st:
                        continue
                    stu_url = f'{st_base}?highlight={st.pk}' if st_base != '#' else '#'
                    notification_all.append({
                        'type': 'admin_student_reg_item',
                        'url': stu_url,
                        'label': f'{st.get_full_name()} ({st.student_id})',
                        'label_right': _('Review'),
                        'icon': 'fa-user-plus',
                        'is_read': False,
                        'time_ago': notification_relative_time(notif.created_at),
                        'show_student_reg_section': j == 0,
                    })
            if admin_staff_reg_unread_count:
                try:
                    psp_url = reverse('pending-staff-personnel-list')
                except Exception:
                    psp_url = '#'
                latest_staff_reg = (
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='staff_personnel_registration',
                    )
                    .order_by('-created_at')
                    .values_list('created_at', flat=True)
                    .first()
                )
                notification_all.append({
                    'type': 'admin_staff_reg_summary',
                    'url': psp_url,
                    'label': f'{admin_staff_reg_unread_count} staff/faculty registration(s)',
                    'label_right': _('Review'),
                    'icon': 'fa-user-shield',
                    'is_read': False,
                    'time_ago': notification_relative_time(latest_staff_reg),
                })
            if admin_incident_only_count:
                _append_unread_incident_nav_items(notification_all, request.user)
        elif _nr_for_notif == 'student affairs' and (
            admin_incident_only_count or admin_student_reg_unread_count
        ):
            if admin_student_reg_unread_count:
                sas_student_reg_items = list(
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='student_registration',
                        related_student_id__isnull=False,
                    ).select_related('related_student').order_by('-created_at')[:15]
                )
                try:
                    st_base = reverse('gate-student-list')
                except Exception:
                    st_base = '#'
                for j, notif in enumerate(sas_student_reg_items):
                    st = notif.related_student
                    if not st:
                        continue
                    stu_url = f'{st_base}?highlight={st.pk}' if st_base != '#' else '#'
                    notification_all.append({
                        'type': 'admin_student_reg_item',
                        'url': stu_url,
                        'label': f'{st.get_full_name()} ({st.student_id})',
                        'label_right': _('Review'),
                        'icon': 'fa-user-plus',
                        'is_read': False,
                        'time_ago': notification_relative_time(notif.created_at),
                        'show_student_reg_section': j == 0,
                    })
            if admin_incident_only_count:
                _append_unread_incident_nav_items(notification_all, request.user)
        elif _nr_for_notif not in ('admin', 'student affairs') and admin_incident_unread_count:
            from gate.models import AdminNotification

            try:
                inc_url = reverse('gate-incident-list')
            except Exception:
                inc_url = '#'
            latest_other_inc = (
                AdminNotification.objects.filter(
                    target_user=request.user,
                    is_read=False,
                    notification_type='incident',
                )
                .order_by('-created_at')
                .values_list('created_at', flat=True)
                .first()
            )
            notification_all.append({
                'type': 'admin_incident_summary',
                'url': inc_url,
                'label': f'{admin_incident_unread_count} gate incident alert(s)',
                'label_right': _('View log'),
                'icon': 'fa-exclamation-triangle',
                'is_read': False,
                'time_ago': notification_relative_time(latest_other_inc),
            })

    if request.user.is_authenticated and (
        pending_staff_personnel or upcoming_events or new_events
    ):
        try:
            events_url = reverse('event-list')
            pending_staff_personnel_url = reverse('pending-staff-personnel-list')
        except Exception:
            events_url = '#'
            pending_staff_personnel_url = '#'

        if pending_staff_personnel_count:
            notification_all.append({
                'type': 'pending_staff_personnel_summary',
                'url': pending_staff_personnel_url,
                'label': f'{pending_staff_personnel_count} staff/faculty pending approval',
                'label_right': '',
                'icon': 'fa-user-shield',
                'is_read': 'notif_pending_staff_personnel' in read_notification_ids,
                'time_ago': notification_relative_time(latest_pending_staff_joined),
            })
        for u in pending_staff_personnel:
            notification_all.append({
                'type': 'staff_personnel',
                'url': pending_staff_personnel_url + '?user_id=' + str(u.pk),
                'label': f'{u.get_full_name() or u.username} ({u.username})',
                'label_right': '',
                'icon': 'fa-user-clock',
                'is_read': u.pk in read_staff_personnel_pks,
                'obj': u,
                'time_ago': notification_relative_time(u.date_joined),
            })

        if new_events_count:
            notification_all.append({
                'type': 'new_events_summary',
                'url': events_url,
                'label': f'{new_events_count} new event(s)',
                'label_right': 'View',
                'icon': 'fa-calendar-plus',
                'is_read': 'notif_new_events' in read_notification_ids,
                'time_ago': notification_relative_time(latest_new_event_created),
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
                'time_ago': notification_relative_time(e.created_date),
            })

        if upcoming_events_count:
            notification_all.append({
                'type': 'events_summary',
                'url': events_url,
                'label': f'{upcoming_events_count} upcoming event(s)',
                'label_right': 'View',
                'icon': 'fa-calendar-alt',
                'is_read': 'notif_upcoming_events' in read_notification_ids,
                'time_ago': notification_relative_time(latest_upcoming_event_created),
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
                'time_ago': notification_relative_time(e.created_date),
            })
    notification_has_more = len(notification_all) > NOTIFICATION_DROPDOWN_MAX

    # Check if user is clocked in (gate shift)
    user_clocked_in = False
    if request.user.is_authenticated:
        try:
            _clk_role = get_user_role(request.user)
        except Exception:
            _clk_role = None
        if _clk_role in ('admin', 'staff', 'faculty'):
            from gate.models import GateShift
            user_clocked_in = GateShift.objects.filter(
                personnel=request.user,
                shift_end__isnull=True
            ).exists()

    return {
        'pending_students_count': pending_students_count,
        'pending_students': pending_students,
        'pending_staff_personnel_count': pending_staff_personnel_count,
        'pending_staff_personnel': pending_staff_personnel,
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
    """Inject site theme (name, logo, primary color) for theming. Cached for anonymous to speed up login."""
    from django.core.cache import cache
    cache_key = 'site_theme_context'
    # Anonymous users (login page): use cache to avoid DB hit every time
    if not request.user.is_authenticated:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    try:
        from gate.models import SiteTheme
        theme = SiteTheme.objects.first()
        if theme:
            result = {
                'site_theme': theme,
                'site_name': theme.site_name,
                'site_primary_color': theme.primary_color or '#28a745',
                'site_logo': theme.logo,
            }
        else:
            result = {
                'site_theme': None,
                'site_name': 'City College of Bayawan',
                'site_primary_color': '#28a745',
                'site_logo': None,
            }
        cache.set(cache_key, result, 300)  # 5 min for all users
        return result
    except Exception:
        pass
    return {
        'site_theme': None,
        'site_name': 'City College of Bayawan',
        'site_primary_color': '#28a745',
        'site_logo': None,
    }



def gate_notifications_context(request):
    """
    Legacy context keys for templates (gate-only notification dropdown removed).
    """
    return {
        'gate_notifications': [],
        'personnel_unread_count': 0,
        'personnel_has_urgent': False,
    }
