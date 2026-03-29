"""
Staff/personnel gate JSON APIs and admin broadcast form.

Legacy separate "guard account" UI and /guard/* routes were removed; staff use the
main dashboard, gate scan, and analytics. These endpoints back lookup, optional
polls, and notifications targeting staff/faculty at the gate.
"""
import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_GET, require_POST

from gate_analytics.roles import get_user_role
from .models import GateNotification, GateShift
from .gate_personnel_services import (
    GateNotificationService,
    GateActivityLogger,
    RealtimeDashboardService,
    StudentLookupService,
)

logger = logging.getLogger(__name__)
# Staff gate scanner only (camera started on /gate/). Guard monitor must NOT set this key.
GATE_STAFF_SCANNER_HEARTBEAT_CACHE_KEY = 'gate_staff_scanner_heartbeat_v2'


def _can_use_gate_tools(user):
    """Staff/faculty/admin may use gate APIs (no separate Guard role)."""
    role = get_user_role(user)
    return role in ('admin', 'staff', 'faculty')


def _can_post_scanner_heartbeat(user):
    """Dashboard + /gate/ scanner session ping; includes Student Affairs (same as main dashboard access)."""
    role = get_user_role(user)
    return role in ('admin', 'staff', 'faculty', 'student affairs')


def _can_send_gate_broadcast(user):
    """Admin or staff may send in-app notifications to gate staff/faculty."""
    role = get_user_role(user)
    return role in ('admin', 'staff')


@login_required
def mark_notification_read_view(request):
    """
    AJAX endpoint to mark notification as read.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    if not _can_use_gate_tools(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    notification_id = request.POST.get('notification_id')
    if not notification_id and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
        except (json.JSONDecodeError, ValueError):
            pass

    if not notification_id:
        return JsonResponse({'success': False, 'error': 'notification_id required'}, status=400)

    try:
        notification_id = int(notification_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid notification_id'}, status=400)

    success = GateNotificationService.mark_as_read(notification_id, request.user)

    if success:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Notification not found or already read'}, status=404)


@login_required
def mark_all_notifications_read_view(request):
    """AJAX endpoint to mark all personnel gate notifications as read for the current user."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    if not _can_use_gate_tools(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    now = timezone.now()
    updated = GateNotification.objects.filter(
        notify_user=request.user,
        is_read=False
    ).update(is_read=True, read_at=now)

    return JsonResponse({'success': True, 'marked': updated})


@login_required
def quick_student_lookup_view(request):
    """Student lookup for gate scan (staff at gate)."""
    if not _can_use_gate_tools(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

    query = request.GET.get('q', '').strip()

    if len(query) < 3:
        return JsonResponse({
            'success': False,
            'error': 'Search query must be at least 3 characters'
        }, status=400)

    student = StudentLookupService.lookup_by_id(query)

    if not student:
        students = StudentLookupService.lookup_by_name(query, limit=10)

        if students.count() == 0:
            GateActivityLogger.log_lookup(
                personnel=request.user,
                query=query,
                results_count=0,
                device_id=request.GET.get('device_id', ''),
                ip_address=request.META.get('REMOTE_ADDR')
            )

            return JsonResponse({
                'success': False,
                'error': 'No students found'
            }, status=404)

        results = []
        for s in students:
            results.append({
                'student_id': s.student_id,
                'name': s.get_full_name(),
                'course': s.course or '—',
                'year_level': s.year_level or '—'
            })

        GateActivityLogger.log_lookup(
            personnel=request.user,
            query=query,
            results_count=len(results),
            device_id=request.GET.get('device_id', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return JsonResponse({
            'success': True,
            'multiple': True,
            'results': results
        })

    today_schedule = StudentLookupService.get_today_schedule(student)
    recent_entries = StudentLookupService.get_recent_entries(student, days=3)

    entry_history = []
    for entry in recent_entries:
        entry_history.append({
            'timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M'),
            'scan_type': entry.scan_type or 'IN',
            'granted': entry.granted,
            'notes': entry.notes or ''
        })

    GateActivityLogger.log_lookup(
        personnel=request.user,
        query=query,
        results_count=1,
        device_id=request.GET.get('device_id', ''),
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return JsonResponse({
        'success': True,
        'multiple': False,
        'student': {
            'student_id': student.student_id,
            'name': student.get_full_name(),
            'course': student.course or '—',
            'year_level': student.year_level or '—',
            'photo_url': student.photo.url if student.photo else None,
            'today_schedule': today_schedule,
            'recent_entries': entry_history
        }
    })


@login_required
def dashboard_stats_api_view(request):
    """AJAX stats for gate/dashboard (staff at gate)."""
    if not _can_use_gate_tools(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    stats = RealtimeDashboardService.get_current_stats()
    stats['timestamp'] = stats['timestamp'].isoformat()
    return JsonResponse({'success': True, 'stats': stats})


def _guard_token_ok(request):
    token = (request.GET.get('token') or '').strip()
    expected = getattr(settings, 'GATE_GUARD_DISPLAY_TOKEN', '') or ''
    return bool(expected) and token == expected


@require_POST
def scanner_heartbeat_view(request):
    """
    Staff gate scanner session ping. Only JSON with camera_running true/false is honored.
    Legacy clients that POST {} no longer refresh TTL — otherwise the guard wall stays 'active'
    without the camera running.
    """
    ttl = getattr(settings, 'GATE_SCANNER_HEARTBEAT_TTL', 90)
    if not request.user.is_authenticated or not _can_post_scanner_heartbeat(request.user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    camera_running = None
    if request.body:
        try:
            body = json.loads(request.body.decode())
            if isinstance(body, dict) and 'camera_running' in body:
                camera_running = bool(body['camera_running'])
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            pass

    if camera_running is None:
        return JsonResponse({'success': True, 'ignored': True})

    if not camera_running:
        cache.delete(GATE_STAFF_SCANNER_HEARTBEAT_CACHE_KEY)
        return JsonResponse({'success': True, 'scanner_active': False})

    user = request.user
    payload = {
        'last_seen': timezone.now().isoformat(),
        'user_id': user.id,
        'username': user.get_username(),
        'display_name': (user.get_full_name() or '').strip() or user.get_username(),
    }
    cache.set(GATE_STAFF_SCANNER_HEARTBEAT_CACHE_KEY, payload, ttl)
    return JsonResponse({'success': True, 'ttl': ttl, 'scanner_active': True})


@require_GET
def guard_dashboard_data_view(request):
    """JSON for guard wall display; requires GATE_GUARD_DISPLAY_TOKEN as ?token= (no login)."""
    if not _guard_token_ok(request):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    hb = cache.get(GATE_STAFF_SCANNER_HEARTBEAT_CACHE_KEY)
    scanner_active = bool(hb)
    minimal = (request.GET.get('minimal') or '').strip().lower() in ('1', 'true', 'yes')
    if minimal:
        return JsonResponse({
            'success': True,
            'scanner_active': scanner_active,
        })
    stats = RealtimeDashboardService.get_current_stats()
    stats['timestamp'] = stats['timestamp'].isoformat()
    scanner = None
    if hb:
        scanner = {
            'last_seen': hb.get('last_seen'),
            'display_name': hb.get('display_name') or hb.get('username') or '',
            'username': hb.get('username') or '',
        }
    recent = RealtimeDashboardService.get_guard_recent_entries(limit=30)
    return JsonResponse({
        'success': True,
        'stats': stats,
        'scanner_active': scanner_active,
        'scanner': scanner,
        'recent_activity': recent,
    })


@login_required
def check_new_notifications_api_view(request):
    """
    Legacy AJAX poll for gate-only notifications (deprecated — use main navbar notifications).
    """
    if not _can_use_gate_tools(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    return JsonResponse({
        'success': True,
        'notifications': [],
        'new_since': [],
        'unread_count': 0,
        'has_urgent': False,
    })


@login_required
def admin_send_gate_notification_view(request):
    """
    Admin view to send custom in-app notifications to staff/faculty at the gate.
    """
    from django.contrib.auth.models import User

    if not _can_send_gate_broadcast(request.user):
        messages.error(request, "Access denied. Admin or staff role required.")
        return redirect('dashboard')

    if request.method == 'POST':
        recipient_type = request.POST.get('recipient_type')
        specific_user_id = (
            request.POST.get('specific_user') or request.POST.get('specific_personnel') or ''
        ).strip()
        priority = request.POST.get('priority', 'medium')
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not title or not message_text:
            messages.error(request, "Title and message are required.")
            return redirect('gate-analytics')

        if recipient_type == 'all':
            recipients = list(
                User.objects.filter(
                    Q(groups__name__iexact='Staff') | Q(groups__name__iexact='Faculty')
                ).distinct()
            )
            broadcast = True
        elif recipient_type == 'on_duty':
            active_shifts = GateShift.objects.filter(shift_end__isnull=True).select_related('personnel')
            recipients = [shift.personnel for shift in active_shifts]
            broadcast = True
        elif recipient_type == 'specific' and specific_user_id:
            try:
                target = User.objects.get(id=specific_user_id)
                if not target.groups.filter(name__iexact='staff').exists() and not target.groups.filter(name__iexact='faculty').exists():
                    raise User.DoesNotExist
                recipients = [target]
                broadcast = False
            except User.DoesNotExist:
                messages.error(request, "Selected user not found or not staff/faculty.")
                return redirect('gate-analytics')
        else:
            messages.error(request, "Invalid recipient selection.")
            return redirect('gate-analytics')

        created_count = 0
        for u in recipients:
            GateNotification.objects.create(
                notification_type='system',
                priority=priority,
                title=title,
                message=message_text,
                notify_user=u,
                broadcast=broadcast
            )
            created_count += 1

        try:
            from gate.notifications import send_announcement_emails
            send_announcement_emails(recipients, title, message_text)
        except Exception:
            pass

        messages.success(request, f"Notification sent to {created_count} recipient(s).")
        return redirect('gate-analytics')

    all_staff = User.objects.filter(
        Q(groups__name__iexact='Staff') | Q(groups__name__iexact='Faculty')
    ).distinct().order_by('username')
    on_duty_count = GateShift.objects.filter(shift_end__isnull=True).count()

    context = {
        'all_staff': all_staff,
        'on_duty_count': on_duty_count,
    }

    return render(request, 'gate/admin_send_gate_notification.html', context)


def _guard_incident_request_authorized(request):
    """Valid GATE_GUARD_DISPLAY_TOKEN or logged-in staff/faculty/admin (gate tools)."""
    token = (request.POST.get('guard_token') or request.headers.get('X-Gate-Guard-Token') or '').strip()
    expected = getattr(settings, 'GATE_GUARD_DISPLAY_TOKEN', '') or ''
    if expected and token == expected:
        return True
    if request.user.is_authenticated and _can_use_gate_tools(request.user):
        return True
    return False


@require_POST
def guard_incident_report_view(request):
    """
    Guard monitor (token) or logged-in gate staff: report incident → SAS / Registrar / both.
    POST: guard_token (optional if staff session), category (id_issue | not_registered | other), optional details, scanned_id.
    """
    if not _guard_incident_request_authorized(request):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    category = (request.POST.get('category') or '').strip()
    if category not in ('id_issue', 'not_registered', 'other'):
        return JsonResponse({'success': False, 'error': 'Invalid category'}, status=400)

    details = (request.POST.get('details') or '').strip()
    scanned_id = (request.POST.get('scanned_id') or '').strip()
    xff = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
    raw_ip = xff or request.META.get('REMOTE_ADDR') or ''
    ip = raw_ip[:45] if raw_ip else None

    try:
        from .guard_incident_report import create_guard_incident_and_notify
        incident = create_guard_incident_and_notify(
            category, details=details, scanned_id=scanned_id, ip_address=ip
        )
    except Exception:
        logger.exception('guard_incident_report')
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)

    return JsonResponse({'success': True, 'incident_id': incident.id})
