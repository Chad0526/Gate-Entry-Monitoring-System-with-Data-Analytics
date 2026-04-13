"""
Middleware to mark navbar notifications as "read" when the user visits the linked page.
Read state is stored in the database (NotificationRead) so it persists across session resets.
"""
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.utils import timezone
from django.db.models import Q

from gate.models import AdminNotification, NotificationRead, Student


def _get_notification_keys(request):
    """Return a list of notification keys to mark as read for this request (0, 1, or 2 keys)."""
    if not request.user.is_authenticated:
        return []
    try:
        resolver_match = resolve(request.path_info)
    except Resolver404:
        resolver_match = None
    name = resolver_match.url_name if resolver_match else None
    kwargs = resolver_match.kwargs if resolver_match else {}
    path = (request.path or '').rstrip('/')

    if name == "gate-student-list" and request.GET.get("pending") == "1":
        return ["notif_pending_students"]
    if name == "gate-student-edit" and kwargs.get("pk"):
        return [f"notif_student_{kwargs['pk']}"]
    if name == "event-list":
        return ["notif_upcoming_events", "notif_new_events"]
    if name == "event-detail" and kwargs.get("pk"):
        return [f"notif_event_{kwargs['pk']}"]
    if name == "gate-entry-list":
        return ["notif_gate_entries"]
    if name == "gate-incident-list":
        return ["notif_incidents"]
    if name == "gate-analytics":
        return ["notif_analytics"]
    # Staff/Faculty/Personnel pending approval (in-app page, not Django admin)
    if name == "pending-staff-personnel-list":
        keys = ["notif_pending_staff_personnel"]
        user_id = request.GET.get("user_id")
        if user_id and user_id.isdigit():
            keys.append(f"notif_staff_personnel_{user_id}")
        return keys
    return []


class NotificationReadMiddleware:
    """Mark a notification as read when the user visits its target URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        keys = _get_notification_keys(request)
        for key in keys:
            if request.user.is_authenticated:
                NotificationRead.objects.get_or_create(
                    user=request.user,
                    notification_key=key,
                )
        # Gate incident alerts (AdminNotification) clear when user opens the incident log
        if request.user.is_authenticated:
            try:
                rm = resolve(request.path_info)
                if rm.url_name == 'gate-incident-list':
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='incident',
                    ).update(is_read=True, read_at=timezone.now())
                if rm.url_name == 'gate-student-edit' and rm.kwargs.get('pk'):
                    pk = rm.kwargs['pk']
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='sas_inactive_ready_activation',
                        related_student_id=pk,
                    ).update(is_read=True, read_at=timezone.now())
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='gate_manual_referral',
                        related_student_id=pk,
                    ).update(is_read=True, read_at=timezone.now())
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='sas_verified_gate_followup',
                        related_student_id=pk,
                    ).update(is_read=True, read_at=timezone.now())
                    st = Student.objects.filter(pk=pk).only('student_id').first()
                    inc_q = Q(related_incident__student_id=pk)
                    if st and (st.student_id or '').strip():
                        inc_q |= Q(
                            related_incident__scanned_id__iexact=(st.student_id or '').strip()
                        )
                    AdminNotification.objects.filter(
                        target_user=request.user,
                        is_read=False,
                        notification_type='incident',
                    ).filter(inc_q).update(is_read=True, read_at=timezone.now())
            except Exception:
                pass
        response = self.get_response(request)
        return response
